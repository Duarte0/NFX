"""Read-only retention eligibility and preview domain services."""

from __future__ import annotations

import calendar
import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import cast
from uuid import UUID

from django.core import signing
from django.db.models import Prefetch, QuerySet
from django.utils import timezone

from nfx.artifacts.models import ArtifactState
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEventEvidence,
    DocumentEvidence,
    DocumentFamily,
    DocumentState,
)

RULE_VERSION = "retention-v1"
_MAX_LIMIT = 100
_MAX_SCAN = 5000
_CURSOR_SALT = "nfx.retention.documents.cursor"
_ALLOWED_KEYS = frozenset(
    {
        "company_id",
        "family",
        "state",
        "eligible_from",
        "eligible_to",
        "as_of",
        "limit",
        "cursor",
        "scope_hash",
    }
)
_FAMILIES = frozenset((DocumentFamily.NFE, DocumentFamily.NFSE))
_STATES = frozenset(("retained", "eligible", "non_executable"))
_SAFE_TEXT = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:/-")


class InvalidRetentionParams(ValueError):
    """A retention read query is invalid or exceeds its bounds."""


class RetentionState(StrEnum):
    RETAINED = "retained"
    ELIGIBLE = "eligible"
    NON_EXECUTABLE = "non_executable"


@dataclass(frozen=True)
class RetentionParams:
    company_id: UUID | None = None
    family: str | None = None
    state: RetentionState | None = None
    eligible_from: date | None = None
    eligible_to: date | None = None
    as_of: date | None = None
    limit: int = 50
    cursor: UUID | None = None


@dataclass(frozen=True)
class RetentionDecision:
    state: RetentionState
    reason_code: str
    rule_version: str
    basis_date: date | None
    eligibility_date: date | None
    calculated_on: date


def _single(query: Mapping[str, object], key: str) -> object | None:
    getlist = getattr(query, "getlist", None)
    if callable(getlist):
        values = list(getlist(key))
        if len(values) > 1:
            raise InvalidRetentionParams("parameter is repeated")
        return values[0] if values else None
    value = query.get(key)
    if isinstance(value, list | tuple):
        if len(value) != 1:
            raise InvalidRetentionParams("parameter is repeated")
        return cast(object, value[0])
    return cast(object | None, value)


def _date(value: object | None) -> date | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InvalidRetentionParams("date is invalid")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidRetentionParams("date is invalid") from exc


def _uuid(value: object | None) -> UUID | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InvalidRetentionParams("identifier is invalid")
    try:
        return UUID(value)
    except ValueError as exc:
        raise InvalidRetentionParams("identifier is invalid") from exc


def _safe_reference(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRetentionParams("parameter is invalid")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or len(normalized) > 64 or any(char not in _SAFE_TEXT for char in normalized):
        raise InvalidRetentionParams("parameter is invalid")
    return normalized


def cursor_for(value: UUID | str) -> str:
    return signing.Signer(salt=_CURSOR_SALT).sign(str(value))


def _cursor(value: object | None) -> UUID | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise InvalidRetentionParams("cursor is invalid")
    try:
        return UUID(signing.Signer(salt=_CURSOR_SALT).unsign(value))
    except (signing.BadSignature, ValueError) as exc:
        raise InvalidRetentionParams("cursor is invalid") from exc


def parse_retention_params(query: Mapping[str, object]) -> RetentionParams:
    unknown = set(query.keys()) - _ALLOWED_KEYS
    if unknown:
        raise InvalidRetentionParams("unsupported filter")
    family = _safe_reference(_single(query, "family"))
    if family is not None and family not in _FAMILIES:
        raise InvalidRetentionParams("family is invalid")
    state_value = _safe_reference(_single(query, "state"))
    if state_value is not None and state_value not in _STATES:
        raise InvalidRetentionParams("state is invalid")
    limit_value = _single(query, "limit")
    if limit_value is None or limit_value == "":
        limit = 50
    else:
        try:
            limit = int(str(limit_value))
        except (TypeError, ValueError) as exc:
            raise InvalidRetentionParams("limit is invalid") from exc
        if not 1 <= limit <= _MAX_LIMIT:
            raise InvalidRetentionParams("limit is invalid")
    eligible_from = _date(_single(query, "eligible_from"))
    eligible_to = _date(_single(query, "eligible_to"))
    if eligible_from is not None and eligible_to is not None and eligible_from > eligible_to:
        raise InvalidRetentionParams("date interval is invalid")
    return RetentionParams(
        company_id=_uuid(_single(query, "company_id")),
        family=family,
        state=RetentionState(state_value) if state_value is not None else None,
        eligible_from=eligible_from,
        eligible_to=eligible_to,
        as_of=_date(_single(query, "as_of")),
        limit=limit,
        cursor=_cursor(_single(query, "cursor")),
    )


def _civil_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    return timezone.localtime(value).date() if timezone.is_aware(value) else value.date()


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def calculate_eligibility_date(
    family: str, emitted_at: datetime | None, authorized_at: datetime | None
) -> date:
    if family == DocumentFamily.NFE:
        basis = _civil_date(authorized_at)
        if basis is None:
            raise ValueError("authorization_date_missing")
        return _add_months(basis, 132)
    if family == DocumentFamily.NFSE:
        basis = _civil_date(emitted_at)
        if basis is None:
            raise ValueError("emission_date_missing")
        return date(basis.year + 6, 1, 1)
    raise ValueError("unsupported_family")


def _artifact_available(row: DocumentEvidence | DocumentEventEvidence) -> bool:
    artifact = row.artifact
    return (
        not row.conflicting
        and artifact.state == ArtifactState.FINALIZED
        and artifact.digest == row.digest
        and artifact.size_bytes == row.size_bytes
        and not artifact.safe_error
    )


def _evidence_reason(document: Document) -> str | None:
    if document.state != DocumentState.PERSISTED:
        return "document_conflict"
    evidence = list(document.evidence.all())
    if not evidence:
        return "evidence_missing"
    for row in evidence:
        if row.conflicting:
            return "evidence_conflict"
        if row.artifact.safe_error:
            return "evidence_malformed"
        if row.artifact.state != ArtifactState.FINALIZED:
            return "evidence_unavailable"
        if not _artifact_available(row):
            return "evidence_changed"
    for event in document.events.all():
        event_evidence = list(event.evidence.all())
        if not event_evidence:
            return "event_evidence_missing"
        for event_row in event_evidence:
            if event_row.conflicting:
                return "event_evidence_conflict"
            if event_row.artifact.safe_error:
                return "event_evidence_malformed"
            if not _artifact_available(event_row):
                return "event_evidence_unavailable"
    return None


def decision_for_document(document: Document, *, as_of: date | None = None) -> RetentionDecision:
    calculated_on = as_of or timezone.localdate()
    try:
        eligibility_date = calculate_eligibility_date(
            document.family, document.emitted_at, document.authorized_at
        )
    except ValueError as exc:
        reason = str(exc)
        basis = _civil_date(
            document.authorized_at
            if document.family == DocumentFamily.NFE
            else document.emitted_at
        )
        return RetentionDecision(
            RetentionState.NON_EXECUTABLE,
            reason,
            RULE_VERSION,
            basis,
            None,
            calculated_on,
        )
    evidence_reason = _evidence_reason(document)
    if evidence_reason is not None:
        basis = _civil_date(
            document.authorized_at if document.family == DocumentFamily.NFE else document.emitted_at
        )
        return RetentionDecision(
            RetentionState.NON_EXECUTABLE,
            evidence_reason,
            RULE_VERSION,
            basis,
            eligibility_date,
            calculated_on,
        )
    basis = _civil_date(
        document.authorized_at if document.family == DocumentFamily.NFE else document.emitted_at
    )
    return RetentionDecision(
        RetentionState.ELIGIBLE if calculated_on >= eligibility_date else RetentionState.RETAINED,
        "retention_complete" if calculated_on >= eligibility_date else "within_retention_period",
        RULE_VERSION,
        basis,
        eligibility_date,
        calculated_on,
    )


def _in_scope(artifact: object) -> bool:
    from nfx.artifacts.models import Artifact

    assert isinstance(artifact, Artifact)
    content_type = artifact.detected_mime_type or artifact.declared_mime_type
    return artifact.logical_class in {"fiscal_original", "fiscal_xml"} or content_type in {
        "application/xml",
        "text/xml",
    }


def _evidence_scope(row: DocumentEvidence | DocumentEventEvidence) -> dict[str, object]:
    artifact = row.artifact
    return {
        "id": str(row.id),
        "artifact_id": str(artifact.id),
        "digest": row.digest,
        "size_bytes": row.size_bytes,
        "conflicting": row.conflicting,
        "state": artifact.state,
        "artifact_digest": artifact.digest,
        "artifact_size_bytes": artifact.size_bytes,
        "version": artifact.version,
        "content_type": artifact.detected_mime_type or artifact.declared_mime_type,
    }


def _scope_data(document: Document) -> dict[str, object]:
    evidence = list(document.evidence.all())
    events: list[dict[str, object]] = []
    for event in document.events.all():
        rows = list(event.evidence.all())
        events.append(
            {
                "id": str(event.id),
                "family": event.family,
                "category": event.category,
                "occurred_at": event.occurred_at.isoformat(),
                "relationship_type": event.relationship_type,
                "evidence": [_evidence_scope(row) for row in rows],
            }
        )
    renders = [
        {
            "id": str(render.id),
            "source_artifact_id": str(render.source_artifact_id),
            "source_digest": render.source_digest,
            "source_artifact": {
                "digest": render.source_artifact.digest,
                "size_bytes": render.source_artifact.size_bytes,
                "version": render.source_artifact.version,
                "state": render.source_artifact.state,
            },
            "renderer_id": render.renderer_id,
            "renderer_version": render.renderer_version,
            "state": render.state,
            "artifact": (
                {
                    "id": str(render.artifact_id),
                    "digest": render.artifact.digest,
                    "size_bytes": render.artifact.size_bytes,
                    "version": render.artifact.version,
                    "state": render.artifact.state,
                }
                if render.artifact_id and render.artifact is not None
                else None
            ),
        }
        for render in document.renders.all()
    ]
    return {
        "document_id": str(document.id),
        "document_state": document.state,
        "family": document.family,
        "evidence": [_evidence_scope(row) for row in evidence],
        "events": events,
        "renders": renders,
    }


def scope_hash(document: Document) -> str:
    canonical = json.dumps(_scope_data(document), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision_payload(decision: RetentionDecision) -> dict[str, object]:
    return {
        "state": decision.state,
        "reason_code": decision.reason_code,
        "rule_version": decision.rule_version,
        "basis_date": decision.basis_date.isoformat() if decision.basis_date else None,
        "eligibility_date": decision.eligibility_date.isoformat()
        if decision.eligibility_date
        else None,
        "calculated_on": decision.calculated_on.isoformat(),
    }


def _artifact_payload(row: DocumentEvidence | DocumentEventEvidence) -> dict[str, object]:
    artifact = row.artifact
    return {
        "id": str(row.id),
        "artifact_id": str(artifact.id),
        "digest_prefix": row.digest[:16],
        "size_bytes": row.size_bytes,
        "content_type": artifact.detected_mime_type or artifact.declared_mime_type,
        "availability": "available" if _artifact_available(row) else "unavailable",
    }


def retention_item(document: Document, *, as_of: date | None = None) -> dict[str, object]:
    decision = decision_for_document(document, as_of=as_of)
    return {
        "id": str(document.id),
        "company_id": str(document.company_id),
        "family": document.family,
        "category": document.category,
        "flow": document.flow,
        "state": decision.state,
        "reason_code": decision.reason_code,
        "rule_version": decision.rule_version,
        "basis_date": decision.basis_date.isoformat() if decision.basis_date else None,
        "eligibility_date": decision.eligibility_date.isoformat()
        if decision.eligibility_date
        else None,
        "calculated_on": decision.calculated_on.isoformat(),
        "scope_hash": scope_hash(document),
        "detail_url": f"/api/retention/documents/{document.id}",
        "preview_url": f"/api/retention/documents/{document.id}/preview",
    }


def _retention_queryset() -> QuerySet[Document]:
    evidence = DocumentEvidence.objects.select_related("artifact").order_by("created_at", "id")
    event_evidence = DocumentEventEvidence.objects.select_related("artifact").order_by(
        "created_at", "id"
    )
    events = DocumentEvent.objects.prefetch_related(
        Prefetch("evidence", queryset=event_evidence)
    ).order_by("occurred_at", "id")
    return Document.objects.prefetch_related(
        Prefetch("evidence", queryset=evidence), Prefetch("events", queryset=events)
    ).order_by("id")


def _matches(item: dict[str, object], params: RetentionParams) -> bool:
    if params.state is not None and item["state"] != params.state:
        return False
    eligibility_date = item["eligibility_date"]
    if params.eligible_from is not None and (
        not isinstance(eligibility_date, str)
        or date.fromisoformat(eligibility_date) < params.eligible_from
    ):
        return False
    if params.eligible_to is not None and (
        not isinstance(eligibility_date, str)
        or date.fromisoformat(eligibility_date) > params.eligible_to
    ):
        return False
    return True


def list_retention_documents(params: RetentionParams) -> dict[str, object]:
    queryset = _retention_queryset()
    if params.company_id is not None:
        queryset = queryset.filter(company_id=params.company_id)
    if params.family is not None:
        queryset = queryset.filter(family=params.family)
    if params.cursor is not None:
        queryset = queryset.filter(id__gt=params.cursor)
    candidates = list(queryset[: _MAX_SCAN + 1])
    scan_exhausted = len(candidates) > _MAX_SCAN
    candidates = candidates[:_MAX_SCAN]
    matches: list[dict[str, object]] = []
    last_scanned: UUID | None = None
    for document in candidates:
        last_scanned = document.id
        item = retention_item(document, as_of=params.as_of)
        if _matches(item, params):
            matches.append(item)
    next_cursor: str | None = None
    if len(matches) > params.limit:
        next_cursor = cursor_for(cast(str, matches[params.limit - 1]["id"]))
        matches = matches[: params.limit]
    elif scan_exhausted and last_scanned is not None:
        next_cursor = cursor_for(last_scanned)
    return {
        "documents": matches,
        "next_cursor": next_cursor,
        "as_of": (params.as_of or timezone.localdate()).isoformat(),
        "rule_version": RULE_VERSION,
    }


def retention_detail(document_id: UUID, *, as_of: date | None = None) -> dict[str, object] | None:
    document = _retention_queryset().filter(pk=document_id).first()
    if document is None:
        return None
    return {
        "document": retention_item(document, as_of=as_of),
        "decision": _decision_payload(decision_for_document(document, as_of=as_of)),
        "preview_url": f"/api/retention/documents/{document.id}/preview",
    }


def retention_preview(
    document_id: UUID, *, as_of: date | None = None, expected_scope_hash: str | None = None
) -> tuple[dict[str, object] | None, bool]:
    document = _retention_queryset().filter(pk=document_id).first()
    if document is None:
        return None, False
    current_hash = scope_hash(document)
    if expected_scope_hash is not None and expected_scope_hash != current_hash:
        return {"reason_code": "scope_changed", "scope_hash": current_hash}, True
    decision = decision_for_document(document, as_of=as_of)
    evidence = list(document.evidence.all())
    event_payload: list[dict[str, object]] = []
    for event in document.events.all():
        event_rows = list(event.evidence.all())
        event_payload.append(
            {
                "id": str(event.id),
                "family": event.family,
                "category": event.category,
                "occurred_at": event.occurred_at.isoformat(),
                "relationship_type": event.relationship_type,
                "evidence": [_artifact_payload(row) for row in event_rows],
            }
        )
    return {
        "document": {
            "id": str(document.id),
            "company_id": str(document.company_id),
            "family": document.family,
            "category": document.category,
            "flow": document.flow,
            "emitted_at": document.emitted_at.isoformat(),
            "authorized_at": document.authorized_at.isoformat()
            if document.authorized_at
            else None,
        },
        "decision": _decision_payload(decision),
        "scope": {"hash": current_hash, "version": "scope-v1"},
        "evidence": [_artifact_payload(row) for row in evidence],
        "events": event_payload,
        "renders": [
            {
                "id": str(render.id),
                "renderer_id": render.renderer_id,
                "renderer_version": render.renderer_version,
                "state": render.state,
                "source_digest": render.source_digest,
                "source_artifact": {
                    "id": str(render.source_artifact_id),
                    "digest_prefix": render.source_artifact.digest[:16],
                    "size_bytes": render.source_artifact.size_bytes,
                    "version": render.source_artifact.version,
                    "availability": (
                        "available"
                        if render.source_artifact.state == ArtifactState.FINALIZED
                        and not render.source_artifact.safe_error
                        else "unavailable"
                    ),
                },
                "artifact": (
                    {
                        "id": str(render.artifact_id),
                        "digest_prefix": render.artifact.digest[:16],
                        "size_bytes": render.artifact.size_bytes,
                        "version": render.artifact.version,
                        "availability": (
                            "available"
                            if render.artifact.state == ArtifactState.FINALIZED
                            and not render.artifact.safe_error
                            else "unavailable"
                        ),
                    }
                    if render.artifact_id and render.artifact is not None
                    else None
                ),
            }
            for render in document.renders.all()
        ],
        "deletion": {"authorized": False, "message": "A prévia não autoriza exclusão."},
    }, False
