"""Versioned, in-process DANFE/DANFSe rendering for preserved XML evidence."""

# The service keeps audit calls and safe payload construction explicit; several
# bounded keyword calls are intentionally verbose at this boundary.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import importlib.metadata
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, cast
from uuid import UUID, uuid4

from defusedxml import ElementTree  # type: ignore[import-untyped]
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from nfx.artifacts.models import ArtifactState
from nfx.artifacts.storage import ArtifactNotReadable, ArtifactStorageService, ObjectStore
from nfx.audit.services import AuditService
from nfx.documents.models import (
    Document,
    DocumentEvidence,
    DocumentRender,
    DocumentRenderState,
    DocumentSituation,
    PdfRepresentation,
)
from nfx.documents.rendering_metrics import rendering_metrics
from nfx.identity.policy import Action, authorize
from nfx.identity.services import SessionIdentity
from nfx.jobs.handlers import HandlerOutcome, register_handler
from nfx.jobs.models import Job, JobPolicy
from nfx.jobs.policy import PolicyNotFound, select_policy
from nfx.jobs.services import JobEngine

RENDERER_ID = "brazilfiscalreport"
PINNED_RENDERER_VERSION = "1.0.1"
PDF_MIME_TYPE = "application/pdf"
PDF_RENDER_JOB_TYPE = "document.render_pdf"
MAX_SOURCE_XML_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 50 * 1024 * 1024
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class RenderError(RuntimeError):
    code = "render_failed"


class RenderAccessDenied(RenderError):
    code = "access_denied"


class RenderUnsupported(RenderError):
    code = "unsupported_document"


class RenderUnavailable(RenderError):
    code = "renderer_unavailable"


class RenderTemporaryFailure(RenderError):
    code = "render_temporary_failure"


class RenderResultState(StrEnum):
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    AVAILABLE = "available"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class RendererMetadata:
    renderer_id: str
    version: str
    representations: tuple[PdfRepresentation, ...]


@dataclass(frozen=True)
class RenderRequestResult:
    render: DocumentRender | None
    state: str
    safe_error: str = ""
    reused: bool = False
    queued: bool = False


def renderer_metadata() -> RendererMetadata:
    """Validate and expose the exact library version used by the worker."""
    try:
        installed = importlib.metadata.version("BrazilFiscalReport")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RenderUnavailable("renderer_unavailable") from exc
    if installed != PINNED_RENDERER_VERSION:
        raise RenderUnavailable("renderer_version_mismatch")
    return RendererMetadata(
        renderer_id=RENDERER_ID,
        version=installed,
        representations=(PdfRepresentation.DANFE, PdfRepresentation.DANFSE),
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_xml(xml: bytes | str) -> Any:
    if isinstance(xml, str):
        encoded = xml.encode("utf-8")
    else:
        encoded = xml
    if not isinstance(encoded, bytes) or not encoded or len(encoded) > MAX_SOURCE_XML_BYTES:
        raise RenderUnsupported("source_size_invalid")
    try:
        return ElementTree.fromstring(encoded)
    except (ElementTree.ParseError, ValueError) as exc:
        raise RenderUnsupported("source_xml_invalid") from exc


def _validate_representation_xml(xml: bytes | str, representation: PdfRepresentation) -> None:
    root = _parse_xml(xml)
    name = _local_name(str(root.tag))
    if representation is PdfRepresentation.DANFE and name not in {"nfe", "nfeproc"}:
        raise RenderUnsupported("nfe_layout_unsupported")
    if representation is PdfRepresentation.DANFSE and name not in {"nfse", "nfseproc"}:
        raise RenderUnsupported("nfse_layout_unsupported")


def _normalize_danfse_xml(xml: bytes | str) -> bytes:
    """Apply the NT 008/2026 v1.02 PIS/COFINS retention presentation rule."""
    root = _parse_xml(xml)
    for trib_fed in root.iter():
        if _local_name(str(trib_fed.tag)) != "tribfed":
            continue
        retention_type = next(
            (
                str(child.text or "").strip()
                for child in trib_fed
                if _local_name(str(child.tag)) == "tpretpiscofins"
            ),
            "",
        )
        if retention_type != "1":
            continue
        values: dict[str, Decimal] = {}
        for child in trib_fed:
            name = _local_name(str(child.tag))
            if name not in {"vretcsll", "vpis", "vcofins"}:
                continue
            try:
                values[name] = Decimal(str(child.text or "0").strip() or "0")
            except InvalidOperation as exc:
                raise RenderUnsupported("source_xml_invalid") from exc
        for child in trib_fed:
            name = _local_name(str(child.tag))
            if name == "vretcsll":
                child.text = f"{sum(values.values(), Decimal('0')):.2f}"
            elif name in {"vpis", "vcofins"}:
                child.text = "0.00"
    return bytes(ElementTree.tostring(root, encoding="utf-8"))


def _situation_flags(xml: bytes, document: Document) -> tuple[bool, bool]:
    root = _parse_xml(xml)
    values = {
        str(child.text or "").strip()
        for child in root.iter()
        if _local_name(child.tag) in {"cStat", "tpSituacao"}
    }
    cancelled = document.situation == DocumentSituation.CANCELLED or bool(
        values & {"101", "135", "136"}
    )
    replaced = bool(values & {"101", "102"}) and (
        document.situation != DocumentSituation.CANCELLED
    )
    return cancelled, replaced


def render_pdf_bytes(
    xml: bytes | str,
    representation: PdfRepresentation | str,
    *,
    cancelled: bool = False,
    replaced: bool = False,
) -> bytes:
    """Render without a filesystem path, subprocess, CLI, or network call."""
    metadata = renderer_metadata()
    try:
        selected = (
            representation
            if isinstance(representation, PdfRepresentation)
            else PdfRepresentation(representation)
        )
    except ValueError as exc:
        raise RenderUnsupported("representation_unsupported") from exc
    if selected not in metadata.representations:
        raise RenderUnsupported("representation_unsupported")
    _validate_representation_xml(xml, selected)
    try:
        if selected is PdfRepresentation.DANFE:
            from brazilfiscalreport.danfe import Danfe, DanfeConfig  # type: ignore[import-untyped]

            generator = Danfe(xml=xml, config=DanfeConfig(watermark_cancelled=cancelled))
        else:
            from brazilfiscalreport.danfse import (  # type: ignore[import-untyped]
                Danfse,
                DanfseConfig,
                FontType,
                Margins,
            )

            config = DanfseConfig(
                margins=Margins(top=2, right=2, bottom=2, left=2),
                font_type=FontType.HELVETICA,
                watermark_cancelled=cancelled,
                watermark_replaced=replaced,
            )
            generator = Danfse(xml=_normalize_danfse_xml(xml), config=config)
        output = generator.output()
    except RenderError:
        raise
    except Exception as exc:
        raise RenderTemporaryFailure("renderer_failed") from exc
    if not isinstance(output, bytes | bytearray):
        raise RenderTemporaryFailure("renderer_empty_output")
    payload = bytes(output)
    if len(payload) > MAX_PDF_BYTES:
        raise RenderTemporaryFailure("pdf_size_limit")
    if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-4096:]:
        raise RenderTemporaryFailure("pdf_integrity_invalid")
    return payload


def _safe_code(value: str) -> str:
    return value if _SAFE_CODE.fullmatch(value) else "render_failed"


def _audit(
    *,
    action: str,
    result: str,
    actor: SessionIdentity | None,
    render: DocumentRender | None = None,
    document_id: UUID | str | None = None,
    representation: PdfRepresentation | str = "",
    renderer_version: str = "",
    reason: str = "",
    correlation_id: str = "",
) -> None:
    selected = str(representation)
    AuditService().append(
        action=action,
        entity_type="document_render",
        entity_id=str(render.id) if render is not None else str(document_id or ""),
        result=result,
        actor_id=actor.user_id if actor else None,
        actor_role=actor.role if actor else "system",
        reason=reason,
        correlation_id=correlation_id or (render.correlation_id if render else ""),
        context={
            "representation": selected[:16],
            "renderer_id": RENDERER_ID,
            "renderer_version": renderer_version[:32],
            "result": result[:32],
        },
    )


def _verified_source(document: Document) -> DocumentEvidence | None:
    return (
        DocumentEvidence.objects.select_related("artifact")
        .filter(
            document=document,
            conflicting=False,
            digest=F("artifact__digest"),
            size_bytes=F("artifact__size_bytes"),
            artifact__state=ArtifactState.FINALIZED,
        )
        .filter(
            Q(artifact__detected_mime_type__in=("application/xml", "text/xml"))
            | Q(artifact__declared_mime_type__in=("application/xml", "text/xml"))
        )
        .order_by("created_at", "id")
        .first()
    )


def _ensure_policy(*, family: str, at: datetime) -> JobPolicy:
    try:
        return select_policy(source=RENDERER_ID, flow=family, at=at)
    except PolicyNotFound:
        # The job owner remains the sole retry-policy owner. This bounded local
        # fallback lets a clean application database enqueue rendering before an
        # operator publishes a more specific policy.
        policy, _ = JobPolicy.objects.get_or_create(
            source_scope=RENDERER_ID,
            flow_scope=family,
            version=1,
            defaults={
                "valid_from": datetime(2020, 1, 1, tzinfo=UTC),
                "retry_limit": 3,
                "backoff_initial_seconds": 1,
                "backoff_cap_seconds": 60,
                "jitter_seconds": 0,
                "cooldown_seconds": 0,
            },
        )
        return policy


def _identity_render(
    document: Document, representation: PdfRepresentation, version: str
) -> DocumentRender | None:
    return (
        DocumentRender.objects.select_for_update()
        .filter(
            document=document,
            pdf_type=representation,
            representation=representation,
            renderer_id=RENDERER_ID,
            renderer_version=version,
        )
        .first()
    )


def request_render(
    *,
    actor: SessionIdentity,
    document_id: UUID | str,
    representation: PdfRepresentation | str | None = None,
    regenerate: bool = False,
    now: datetime | None = None,
) -> RenderRequestResult:
    """Authorize, reuse, or enqueue one render identity atomically."""
    rendering_metrics.record("request")
    if not authorize(actor.role, Action.READ_DOCUMENTS, actor_id=actor.user_id):
        rendering_metrics.record("denied")
        _audit(
            action="document.render.denied",
            result="denied",
            actor=actor,
            document_id=document_id,
            reason="access_denied",
        )
        raise RenderAccessDenied("access_denied")
    try:
        document_uuid = UUID(str(document_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise RenderUnsupported("document_reference_invalid") from exc
    current = now or timezone.now()
    if timezone.is_naive(current):
        raise ValueError("now must be timezone-aware")
    document = Document.objects.select_related("company").filter(pk=document_uuid).first()
    if document is None:
        return RenderRequestResult(None, RenderResultState.UNAVAILABLE, "document_not_found")
    try:
        metadata = renderer_metadata()
    except RenderUnavailable as exc:
        rendering_metrics.record("failure")
        _audit(
            action="document.render.request",
            result="unavailable",
            actor=actor,
            document_id=document.id,
            reason=exc.code,
        )
        return RenderRequestResult(None, RenderResultState.UNAVAILABLE, exc.code)
    try:
        selected = (
            representation
            if isinstance(representation, PdfRepresentation)
            else PdfRepresentation(representation)
            if representation is not None
            else PdfRepresentation.for_family(document.family)
        )
    except (TypeError, ValueError):
        _audit(
            action="document.render.request",
            result="unsupported",
            actor=actor,
            document_id=document.id,
            reason="representation_unsupported",
        )
        return RenderRequestResult(
            None, RenderResultState.UNSUPPORTED, "representation_unsupported"
        )
    if selected is not PdfRepresentation.for_family(document.family):
        _audit(
            action="document.render.request",
            result="unsupported",
            actor=actor,
            document_id=document.id,
            representation=selected,
            renderer_version=metadata.version,
            reason="family_representation_mismatch",
        )
        return RenderRequestResult(
            None, RenderResultState.UNSUPPORTED, "family_representation_mismatch"
        )
    source = _verified_source(document)
    if source is None:
        _audit(
            action="document.render.request",
            result="unavailable",
            actor=actor,
            document_id=document.id,
            representation=selected,
            renderer_version=metadata.version,
            reason="source_unavailable",
        )
        return RenderRequestResult(None, RenderResultState.UNAVAILABLE, "source_unavailable")
    try:
        with transaction.atomic():
            locked_document = Document.objects.select_for_update().get(pk=document.id)
            locked_source = _verified_source(locked_document)
            if locked_source is None:
                return RenderRequestResult(
                    None, RenderResultState.UNAVAILABLE, "source_unavailable"
                )
            render = _identity_render(locked_document, selected, metadata.version)
            if render is not None and render.state == DocumentRenderState.FINALIZED:
                if _render_artifact_is_valid(render):
                    _audit(
                        action="document.render.reuse",
                        result="reused",
                        actor=actor,
                        render=render,
                        representation=selected,
                        renderer_version=metadata.version,
                    )
                    rendering_metrics.record("reuse")
                    if regenerate:
                        rendering_metrics.record("regeneration")
                    return RenderRequestResult(render, RenderResultState.AVAILABLE, reused=True)
                render.state = DocumentRenderState.DIVERGENT
                render.safe_error = "artifact_unavailable"
                render.save(update_fields=["state", "safe_error", "updated_at"])
            if render is None:
                render = DocumentRender.objects.create(
                    document=locked_document,
                    source_artifact=locked_source.artifact,
                    pdf_type=selected,
                    representation=selected,
                    renderer_id=metadata.renderer_id,
                    renderer_version=metadata.version,
                    source_digest=locked_source.digest,
                    correlation_id=f"render:{uuid4()}",
                )
            else:
                render.source_artifact = locked_source.artifact
                render.source_digest = locked_source.digest
                render.state = DocumentRenderState.PENDING
                render.safe_error = ""
                render.safe_result = {}
                render.artifact = None
                render.digest = ""
                render.size_bytes = None
                render.finalized_at = None
                render.save(
                    update_fields=[
                        "source_artifact",
                        "source_digest",
                        "state",
                        "safe_error",
                        "safe_result",
                        "artifact",
                        "digest",
                        "size_bytes",
                        "finalized_at",
                        "updated_at",
                    ]
                )
            policy = _ensure_policy(family=locked_document.family, at=current)
            job = JobEngine().enqueue(
                job_type=PDF_RENDER_JOB_TYPE,
                logical_target=f"render:{render.id}",
                payload={
                    "render_id": str(render.id),
                    "document_id": str(locked_document.id),
                    "source_artifact_id": str(locked_source.artifact_id),
                    "representation": str(selected),
                    "renderer_version": metadata.version,
                    "actor_id": actor.user_id,
                },
                idempotency_key=f"render:{render.id}",
                policy=policy,
                scheduled_at=current,
            )
            render.job = job
            render.save(update_fields=["job", "updated_at"])
            _audit(
                action="document.render.regeneration" if regenerate else "document.render.request",
                result="queued",
                actor=actor,
                render=render,
                representation=selected,
                renderer_version=metadata.version,
            )
            rendering_metrics.record("regeneration" if regenerate else "queued")
            return RenderRequestResult(render, RenderResultState.PENDING, queued=True)
    except IntegrityError as exc:
        existing = _identity_render(document, selected, metadata.version)
        if existing is not None:
            return RenderRequestResult(
                existing, existing.state, reused=existing.state == DocumentRenderState.FINALIZED
            )
        raise RenderTemporaryFailure("render_identity_conflict") from exc


def _render_artifact_is_valid(render: DocumentRender) -> bool:
    artifact = render.artifact
    return bool(
        artifact is not None
        and artifact.state == ArtifactState.FINALIZED
        and artifact.digest == render.digest
        and artifact.size_bytes == render.size_bytes
        and artifact.declared_mime_type == PDF_MIME_TYPE
        and artifact.detected_mime_type == PDF_MIME_TYPE
        and render.mime_type == PDF_MIME_TYPE
    )


def _failure_state(render_id: UUID, code: str, *, actor: SessionIdentity | None = None) -> None:
    render = DocumentRender.objects.get(pk=render_id)
    with transaction.atomic():
        render = DocumentRender.objects.select_for_update().get(pk=render_id)
        if render.state == DocumentRenderState.FINALIZED:
            return
        render.state = DocumentRenderState.FAILED
        render.safe_error = _safe_code(code)
        render.safe_result = {}
        render.save(update_fields=["state", "safe_error", "safe_result", "updated_at"])
        _audit(
            action="document.render.failure",
            result="failed",
            actor=actor,
            render=render,
            representation=render.representation,
            renderer_version=render.renderer_version,
            reason=_safe_code(code),
        )
    rendering_metrics.record("failure")


def render_pdf_job(
    render_id: UUID | str,
    *,
    storage: ArtifactStorageService | None = None,
    actor_id: str | None = None,
) -> HandlerOutcome:
    started = time.monotonic()
    try:
        parsed_id = UUID(str(render_id))
    except (TypeError, ValueError, AttributeError):
        return HandlerOutcome.permanent(error_code="render_reference_invalid")
    render = (
        DocumentRender.objects.select_related("document", "source_artifact", "artifact")
        .filter(pk=parsed_id)
        .first()
    )
    if render is None:
        return HandlerOutcome.permanent(error_code="render_reference_missing")
    if render.state == DocumentRenderState.FINALIZED and _render_artifact_is_valid(render):
        return HandlerOutcome.success(
            {"state": DocumentRenderState.FINALIZED, "renderer_version": render.renderer_version}
        )
    if actor_id:
        from nfx.identity.models import User

        actor = User.objects.filter(pk=actor_id, active=True).values("id", "role").first()
        if actor is None or not authorize(
            str(actor["role"]), Action.READ_DOCUMENTS, actor_id=str(actor["id"])
        ):
            _failure_state(parsed_id, "authorization_revoked")
            return HandlerOutcome.permanent(error_code="authorization_revoked")
    rendering_metrics.record("start")
    try:
        metadata = renderer_metadata()
        representation = PdfRepresentation(render.representation)
        if metadata.version != render.renderer_version:
            raise RenderUnavailable("renderer_version_mismatch")
        evidence = (
            DocumentEvidence.objects.filter(
                document_id=render.document_id,
                artifact_id=render.source_artifact_id,
                conflicting=False,
                digest=render.source_digest,
                size_bytes=F("artifact__size_bytes"),
                artifact__state=ArtifactState.FINALIZED,
            )
            .filter(
                Q(artifact__detected_mime_type__in=("application/xml", "text/xml"))
                | Q(artifact__declared_mime_type__in=("application/xml", "text/xml"))
            )
            .select_related("artifact")
            .first()
        )
        if evidence is None or evidence.artifact.digest != render.source_digest:
            raise RenderTemporaryFailure("source_unavailable")
        reader = storage or ArtifactStorageService(_default_store())
        stream = reader.read_verified(evidence.artifact.id)
        try:
            source_xml = stream.read()
        finally:
            stream.close()
        cancelled, replaced = _situation_flags(source_xml, render.document)
        payload = render_pdf_bytes(
            source_xml, representation, cancelled=cancelled, replaced=replaced
        )
        output_store = storage or ArtifactStorageService(
            _default_store(), maximum_size=MAX_PDF_BYTES
        )
        artifact = output_store.begin(
            "document_derived_pdf",
            f"render:{render.id}",
            PDF_MIME_TYPE,
        )
        artifact = output_store.transmit(artifact.id, [payload])
        if not _render_artifact_is_valid_metadata(artifact, payload):
            raise RenderTemporaryFailure("pdf_storage_integrity")
        with transaction.atomic():
            locked = DocumentRender.objects.select_for_update().get(pk=render.id)
            if locked.state == DocumentRenderState.FINALIZED and _render_artifact_is_valid(locked):
                return HandlerOutcome.success(
                    {
                        "state": DocumentRenderState.FINALIZED,
                        "renderer_version": locked.renderer_version,
                    }
                )
            locked.artifact = artifact
            locked.digest = artifact.digest
            locked.size_bytes = artifact.size_bytes
            locked.mime_type = PDF_MIME_TYPE
            locked.state = DocumentRenderState.FINALIZED
            locked.safe_error = ""
            locked.safe_result = {
                "renderer_id": RENDERER_ID,
                "renderer_version": locked.renderer_version,
                "representation": locked.representation,
                "size_bytes": int(artifact.size_bytes or 0),
                "mime_type": PDF_MIME_TYPE,
            }
            locked.finalized_at = timezone.now()
            locked.save(
                update_fields=[
                    "artifact",
                    "digest",
                    "size_bytes",
                    "mime_type",
                    "state",
                    "safe_error",
                    "safe_result",
                    "finalized_at",
                    "updated_at",
                ]
            )
            _audit(
                action="document.render.success",
                result="success",
                actor=None,
                render=locked,
                representation=locked.representation,
                renderer_version=locked.renderer_version,
            )
        rendering_metrics.record("success", duration_ms=(time.monotonic() - started) * 1000)
        return HandlerOutcome.success(
            {
                "state": DocumentRenderState.FINALIZED,
                "renderer_version": render.renderer_version,
                "representation": render.representation,
            }
        )
    except RenderUnsupported as exc:
        _failure_state(parsed_id, exc.code)
        DocumentRender.objects.filter(pk=parsed_id).update(
            state=DocumentRenderState.UNSUPPORTED,
            safe_error=_safe_code(exc.code),
            updated_at=timezone.now(),
        )
        return HandlerOutcome.success({"state": DocumentRenderState.UNSUPPORTED})
    except (ArtifactNotReadable, RenderUnavailable, RenderTemporaryFailure) as exc:
        try:
            code = exc.code if isinstance(exc, RenderError) else "artifact_unavailable"
            _failure_state(parsed_id, code)
        except Exception:
            return HandlerOutcome.temporary(error_code="render_audit_unavailable")
        return HandlerOutcome.temporary(error_code=_safe_code(code))
    except Exception:
        try:
            _failure_state(parsed_id, "renderer_failed")
        except Exception:
            return HandlerOutcome.temporary(error_code="render_audit_unavailable")
        return HandlerOutcome.temporary(error_code="renderer_failed")


def _render_artifact_is_valid_metadata(artifact: Any, payload: bytes) -> bool:
    return bool(
        artifact.state == ArtifactState.FINALIZED
        and artifact.digest == hashlib.sha256(payload).hexdigest()
        and artifact.size_bytes == len(payload)
        and artifact.declared_mime_type == PDF_MIME_TYPE
        and artifact.detected_mime_type == PDF_MIME_TYPE
    )


def _default_store() -> ObjectStore:
    from nfx.artifacts.storage import object_store_from_environment

    return cast(ObjectStore, object_store_from_environment())


def render_handler(job: Job) -> HandlerOutcome:
    render_id = job.payload.get("render_id")
    actor_id = job.payload.get("actor_id")
    return render_pdf_job(str(render_id), actor_id=str(actor_id) if actor_id else None)


def ensure_render_handler() -> None:
    register_handler(PDF_RENDER_JOB_TYPE, render_handler)


def current_render(
    document: Document, representation: PdfRepresentation | str | None = None
) -> DocumentRender | None:
    metadata = renderer_metadata()
    selected = (
        representation
        if isinstance(representation, PdfRepresentation)
        else PdfRepresentation(representation)
        if representation
        else PdfRepresentation.for_family(document.family)
    )
    return (
        DocumentRender.objects.select_related("artifact")
        .filter(
            document=document,
            pdf_type=selected,
            representation=selected,
            renderer_id=RENDERER_ID,
            renderer_version=metadata.version,
        )
        .first()
    )


def render_payload(
    document: Document, representation: PdfRepresentation | str | None = None
) -> dict[str, object]:
    try:
        metadata = renderer_metadata()
        selected = (
            representation
            if isinstance(representation, PdfRepresentation)
            else PdfRepresentation(representation)
            if representation
            else PdfRepresentation.for_family(document.family)
        )
    except (RenderUnavailable, ValueError):
        return {
            "state": RenderResultState.UNAVAILABLE,
            "safe_error": "renderer_unavailable",
            "renderer_id": RENDERER_ID,
            "renderer_version": PINNED_RENDERER_VERSION,
            "representation": None,
            "pdf_type": None,
            "request_url": f"/api/documents/{document.id}/pdf/render",
            "download_url": None,
        }
    render = current_render(document, selected)
    if render is None:
        return {
            "state": RenderResultState.UNAVAILABLE,
            "renderer_id": metadata.renderer_id,
            "renderer_version": metadata.version,
            "representation": selected,
            "pdf_type": selected,
            "request_url": f"/api/documents/{document.id}/pdf/render",
            "download_url": None,
        }
    available = render.state == DocumentRenderState.FINALIZED and _render_artifact_is_valid(render)
    state = (
        RenderResultState.AVAILABLE
        if available
        else (
            RenderResultState.PENDING
            if render.state == DocumentRenderState.PENDING
            else RenderResultState.FAILED
            if render.state
            in {
                DocumentRenderState.FAILED,
                DocumentRenderState.MISSING,
                DocumentRenderState.DIVERGENT,
            }
            else RenderResultState.UNSUPPORTED
        )
    )
    return {
        "id": str(render.id),
        "state": state,
        "safe_error": None if available else render.safe_error or "render_unavailable",
        "renderer_id": render.renderer_id,
        "renderer_version": render.renderer_version,
        "representation": render.representation,
        "pdf_type": render.pdf_type,
        "digest_prefix": render.digest[:16] if available else None,
        "size_bytes": render.size_bytes if available else None,
        "content_type": PDF_MIME_TYPE if available else None,
        "request_url": f"/api/documents/{document.id}/pdf/render",
        "download_url": f"/api/documents/{document.id}/pdf" if available else None,
    }
