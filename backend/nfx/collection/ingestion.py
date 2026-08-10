"""Durable, simulator-safe fiscal page ingestion.

Collection owns continuation state here.  The adapter only supplies bounded
references; artifact storage owns bytes and documents owns identity semantics.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import cast
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from nfx.adapters.simulation import FiscalOutcome, FiscalResponse, FiscalUnit
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import ArtifactStorageService
from nfx.audit.services import AuditService
from nfx.collection.models import (
    INGESTION_TERMINAL_UNIT_STATES,
    CollectionExecution,
    IngestionCheckpoint,
    IngestionPage,
    IngestionPageState,
    ReceivedUnit,
    ReceivedUnitState,
)
from nfx.documents.models import DocumentFamily, DocumentRelationship, DocumentSituation
from nfx.documents.services import (
    DocumentInput,
    FiscalIdentity,
    InvalidDocumentInput,
    persist_document,
)

_REFERENCE = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FAMILY = {"nfe", "adn", "nfse"}
_FAILURE_RESPONSE_OUTCOMES = {
    FiscalOutcome.NO_COVERAGE,
    FiscalOutcome.UNAVAILABLE,
    FiscalOutcome.TIMEOUT,
    FiscalOutcome.COOLDOWN,
    FiscalOutcome.BLOCKED,
    FiscalOutcome.MALFORMED,
    FiscalOutcome.EVENT_WITHOUT_PARENT,
    FiscalOutcome.REPEATED_CURSOR,
}


class IngestionError(RuntimeError):
    """Safe ingestion failure; caller input and external exceptions are omitted."""


class IngestionPositionError(IngestionError):
    pass


class UnitOutcome(StrEnum):
    PENDING = "pending"
    PERSISTED = "persisted"
    REPLAY = "replay"
    QUARANTINE = "quarantine"
    CONFLICT = "conflict"
    FAILED = "failed"


@dataclass(frozen=True)
class IngestionContext:
    company_id: UUID | str
    family: str
    flow: str
    source: str = "synthetic"
    execution_ref: str = "execution:synthetic"
    correlation_id: str = "correlation:synthetic"
    request_cursor: str | None = None
    request_nsu: str | None = None
    execution_id: UUID | str | None = None

    def validate(self) -> None:
        try:
            UUID(str(self.company_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise IngestionError("company reference is invalid") from exc
        if self.family not in _FAMILY:
            raise IngestionError("fiscal family is unsupported")
        for value in (self.flow, self.source, self.execution_ref, self.correlation_id):
            if not isinstance(value, str) or not _REFERENCE.fullmatch(value):
                raise IngestionError("ingestion reference is invalid")
        if self.request_cursor is not None and self.request_nsu is not None:
            raise IngestionError("request cannot contain both cursor and NSU")
        position: str | None
        for position in (self.request_cursor, self.request_nsu):
            if position is not None and not _REFERENCE.fullmatch(position):
                raise IngestionError("request continuation is invalid")


@dataclass(frozen=True)
class IngestionDocumentMetadata:
    emitted_at: datetime
    identity: FiscalIdentity
    role: str = "entrada"
    category: str = "document"
    authorized_at: datetime | None = None
    situation: str = DocumentSituation.UNKNOWN
    parent_document_id: UUID | str | None = None
    relationship_type: str | None = None


@dataclass(frozen=True)
class IngestionResult:
    page_id: UUID
    page_state: IngestionPageState
    unit_states: tuple[UnitOutcome, ...]
    advanced: bool
    next_cursor: str | None
    next_nsu: str | None
    safe_reason: str = ""


DocumentMetadataFactory = Callable[[FiscalUnit, IngestionContext], IngestionDocumentMetadata]
PayloadFactory = Callable[[FiscalUnit], Iterable[bytes]]


def synthetic_payload(unit: FiscalUnit) -> tuple[bytes, ...]:
    """Materialize only the deterministic synthetic marker, never fiscal content."""
    payload = f"nfx-synthetic-unit:{unit.identity}".encode()
    if hashlib.sha256(payload).hexdigest() != unit.content_hash:
        raise IngestionError("synthetic unit hash does not match its reference")
    return (payload,)


def _document_family(family: str) -> str:
    return DocumentFamily.NFE if family == "nfe" else DocumentFamily.NFSE


def _default_metadata(unit: FiscalUnit, context: IngestionContext) -> IngestionDocumentMetadata:
    return IngestionDocumentMetadata(
        emitted_at=timezone.now(),
        identity=FiscalIdentity(external_id=unit.identity),
        category=unit.kind,
        parent_document_id=None,
        relationship_type=DocumentRelationship.EVENT if unit.kind == "event" else None,
    )


def _safe_reason(value: str) -> str:
    if value and re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value):
        return value
    return "ingestion_failure"


class FiscalIngestionService:
    def __init__(
        self,
        storage: ArtifactStorageService,
        *,
        payload_factory: PayloadFactory = synthetic_payload,
        metadata_factory: DocumentMetadataFactory = _default_metadata,
        clock: Callable[[], datetime] = timezone.now,
    ) -> None:
        self.storage = storage
        self.payload_factory = payload_factory
        self.metadata_factory = metadata_factory
        self.clock = clock

    def ingest(self, context: IngestionContext, response: FiscalResponse) -> IngestionResult:
        context.validate()
        self._validate_response_position(context, response)
        page, created = self._register_page(context, response)
        if not created:
            return self._result_for_page(page)
        if page.state == IngestionPageState.FAILED:
            return self._result_for_page(page)

        if response.outcome in _FAILURE_RESPONSE_OUTCOMES:
            return self._finish_failed_page(
                page, _safe_reason(response.error_code or response.outcome.value)
            )

        unit_states: list[UnitOutcome] = []
        for unit in response.units:
            received = self._register_unit(page, context, unit)
            unit_states.append(self._process_unit(received, context, unit))

        page.refresh_from_db()
        if response.outcome == FiscalOutcome.PARTIAL:
            return self._finish_page(
                page, IngestionPageState.PARTIAL, unit_states, "partial_response"
            )
        if any(state == UnitOutcome.FAILED for state in unit_states):
            return self._finish_page(page, IngestionPageState.PARTIAL, unit_states, "unit_pending")
        state = IngestionPageState.EMPTY if not response.units else IngestionPageState.COMPLETE
        return self._finish_page(page, state, unit_states)

    def reconcile(self, *, unit_id: UUID | str | None = None) -> int:
        query = ReceivedUnit.objects.filter(
            state__in=(ReceivedUnitState.PENDING, ReceivedUnitState.FAILED)
        )
        if unit_id is not None:
            query = query.filter(id=unit_id)
        repaired = 0
        for unit in query.select_related("page", "company").order_by("first_seen_at"):
            page = unit.page
            context = IngestionContext(
                company_id=unit.company_id,
                family=unit.family,
                flow=unit.flow,
                execution_ref=f"execution:{page.execution_id or page.id}",
                correlation_id=f"correlation:{page.id}",
                request_cursor=page.request_cursor or None,
                request_nsu=page.request_nsu or None,
                execution_id=page.execution_id,
            )
            result = self._process_unit(unit, context, self._unit_from_record(unit))
            if result != UnitOutcome.FAILED:
                repaired += 1
            page.refresh_from_db()
            states = list(page.units.values_list("state", flat=True))
            if (
                page.state == IngestionPageState.PARTIAL
                and states
                and all(state in INGESTION_TERMINAL_UNIT_STATES for state in states)
                and page.adapter_outcome != FiscalOutcome.PARTIAL.value
            ):
                target = (
                    IngestionPageState.EMPTY if not page.unit_count else IngestionPageState.COMPLETE
                )
                self._finish_page(
                    page,
                    target,
                    [UnitOutcome(state) for state in states],
                )
        for page in IngestionPage.objects.filter(
            state__in=(IngestionPageState.PENDING, IngestionPageState.PARTIAL)
        ).order_by("created_at"):
            states = list(page.units.values_list("state", flat=True))
            if (
                (not page.unit_count or len(states) == page.unit_count)
                and all(state in INGESTION_TERMINAL_UNIT_STATES for state in states)
                and page.adapter_outcome != FiscalOutcome.PARTIAL.value
            ):
                target = (
                    IngestionPageState.EMPTY
                    if not page.unit_count
                    else IngestionPageState.COMPLETE
                )
                self._finish_page(
                    page,
                    target,
                    [UnitOutcome(state) for state in states],
                )
        return repaired

    def _register_page(
        self, context: IngestionContext, response: FiscalResponse
    ) -> tuple[IngestionPage, bool]:
        page_key = f"cursor:{context.request_cursor}" if context.request_cursor else (
            f"nsu:{context.request_nsu}" if context.request_nsu else "initial"
        )
        try:
            with transaction.atomic():
                checkpoint, _ = IngestionCheckpoint.objects.select_for_update().get_or_create(
                    company_id=context.company_id, family=context.family, flow=context.flow
                )
                existing = IngestionPage.objects.filter(
                    company_id=context.company_id,
                    family=context.family,
                    flow=context.flow,
                    page_key=page_key,
                ).first()
                if existing is not None:
                    return existing, False
                expected = checkpoint.cursor if context.family == "nfe" else checkpoint.nsu
                requested = (
                    context.request_cursor if context.family == "nfe" else context.request_nsu
                )
                safe_error = ""
                state = IngestionPageState.PENDING
                if expected != (requested or ""):
                    state = IngestionPageState.FAILED
                    safe_error = "stale_cursor" if requested else "checkpoint_position_mismatch"
                page = IngestionPage.objects.create(
                    company_id=context.company_id,
                    execution_id=context.execution_id,
                    family=context.family,
                    flow=context.flow,
                    page_key=page_key,
                    request_cursor=context.request_cursor or "",
                    request_nsu=context.request_nsu or "",
                    next_cursor=response.next_cursor or "",
                    next_nsu=response.next_nsu or "",
                    adapter_outcome=response.outcome.value,
                    coverage=response.coverage.value,
                    state=state,
                    safe_error=safe_error,
                    unit_count=len(response.units),
                )
                if state == IngestionPageState.FAILED:
                    self._audit(page, "failed", safe_error)
                return page, True
        except IntegrityError:
            page = IngestionPage.objects.get(
                company_id=context.company_id,
                family=context.family,
                flow=context.flow,
                page_key=page_key,
            )
            return page, False

    def _register_unit(
        self, page: IngestionPage, context: IngestionContext, unit: FiscalUnit
    ) -> ReceivedUnit:
        try:
            with transaction.atomic():
                received, created = ReceivedUnit.objects.select_for_update().get_or_create(
                    page=page,
                    identity=unit.identity,
                    defaults={
                        "company_id": context.company_id,
                        "family": context.family,
                        "flow": context.flow,
                        "kind": unit.kind,
                        "parent_identity": unit.parent_identity or "",
                        "content_hash": unit.content_hash,
                        "state": ReceivedUnitState.PENDING,
                    },
                )
                if not created and received.content_hash != unit.content_hash:
                    received.state = ReceivedUnitState.PENDING
                    received.safe_reason = "content_hash_changed"
                    received.save(update_fields=["state", "safe_reason", "updated_at"])
                return received
        except IntegrityError:
            return ReceivedUnit.objects.select_for_update().get(
                page=page, identity=unit.identity
            )

    def _process_unit(
        self, received: ReceivedUnit, context: IngestionContext, unit: FiscalUnit
    ) -> UnitOutcome:
        if (
            received.state in INGESTION_TERMINAL_UNIT_STATES
            and received.content_hash == unit.content_hash
        ):
            return UnitOutcome(received.state)
        now = self.clock()
        ReceivedUnit.objects.filter(pk=received.pk).update(
            attempts=received.attempts + 1, last_attempt_at=now, updated_at=now
        )
        try:
            artifact = self._ensure_artifact(received, context, unit)
        except Exception:
            self._fail_unit(received, "object_unavailable")
            return UnitOutcome.FAILED

        try:
            metadata = self.metadata_factory(unit, context)
            if unit.kind == "event" and metadata.parent_document_id is None:
                parent = (
                    ReceivedUnit.objects.filter(
                        company_id=context.company_id,
                        family=context.family,
                        flow=context.flow,
                        identity=unit.parent_identity or "",
                        document_id__isnull=False,
                    )
                    .order_by("first_seen_at")
                    .first()
                )
                if parent is None:
                    self._finish_unit(received, artifact, UnitOutcome.QUARANTINE, "parent_missing")
                    return UnitOutcome.QUARANTINE
                metadata = IngestionDocumentMetadata(
                    **{**metadata.__dict__, "parent_document_id": parent.document_id}
                )
            data = DocumentInput(
                company_id=context.company_id,
                family=_document_family(context.family),
                role=metadata.role,
                category=metadata.category,
                source=context.source,
                flow=context.flow,
                identity=metadata.identity,
                emitted_at=metadata.emitted_at,
                authorized_at=metadata.authorized_at,
                situation=metadata.situation,
                artifact_id=artifact.id,
                origin_execution_ref=context.execution_ref,
                correlation_id=context.correlation_id,
                kind="event" if unit.kind == "event" else "document",
                parent_document_id=metadata.parent_document_id,
                relationship_type=metadata.relationship_type,
            )
            persisted = persist_document(data)
        except InvalidDocumentInput:
            self._fail_unit(received, "document_input_invalid")
            return UnitOutcome.FAILED
        outcome = UnitOutcome(persisted.status.value)
        self._finish_unit(
            received,
            artifact,
            outcome,
            persisted.reason_code or "",
            document_id=persisted.document_id,
            event_id=persisted.event_id,
        )
        return outcome

    def _ensure_artifact(
        self, received: ReceivedUnit, context: IngestionContext, unit: FiscalUnit
    ) -> Artifact:
        if received.artifact_id:
            current = Artifact.objects.get(pk=received.artifact_id)
            if current.state == ArtifactState.FINALIZED and current.digest == unit.content_hash:
                return current
        scope_hash = hashlib.sha256(
            f"{context.company_id}:{context.family}:{context.flow}:{unit.identity}".encode()
        ).hexdigest()[:32]
        logical_key = f"ingestion:{scope_hash}:{unit.content_hash}"
        existing = Artifact.objects.filter(logical_key=logical_key).order_by("created_at").first()
        if existing is None:
            existing = self.storage.begin(
                "fiscal_original", logical_key, "application/octet-stream"
            )
        if existing.state != ArtifactState.FINALIZED:
            existing = self.storage.transmit(existing.id, self.payload_factory(unit))
        if existing.digest != unit.content_hash:
            raise IngestionError("stored object digest does not match unit reference")
        ReceivedUnit.objects.filter(pk=received.pk).update(
            artifact_id=existing.id, updated_at=self.clock()
        )
        return existing

    def _finish_unit(
        self,
        received: ReceivedUnit,
        artifact: Artifact,
        outcome: UnitOutcome,
        reason: str = "",
        *,
        document_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> None:
        now = self.clock()
        values: dict[str, object] = {
            "artifact_id": artifact.id,
            "state": outcome.value,
            "safe_reason": _safe_reason(reason) if reason else "",
            "terminal_at": now,
            "updated_at": now,
        }
        if document_id:
            values["document_id"] = document_id
        if event_id:
            values["event_id"] = event_id
        ReceivedUnit.objects.filter(pk=received.pk).update(**values)

    def _fail_unit(self, received: ReceivedUnit, reason: str) -> None:
        ReceivedUnit.objects.filter(pk=received.pk).update(
            state=ReceivedUnitState.FAILED,
            safe_reason=_safe_reason(reason),
            updated_at=self.clock(),
        )

    def _finish_failed_page(self, page: IngestionPage, reason: str) -> IngestionResult:
        return self._finish_page(page, IngestionPageState.FAILED, [], reason)

    def _finish_page(
        self,
        page: IngestionPage,
        state: IngestionPageState,
        unit_states: list[UnitOutcome],
        reason: str = "",
    ) -> IngestionResult:
        advanced = False
        with transaction.atomic():
            page = IngestionPage.objects.select_for_update().get(pk=page.pk)
            if page.state == IngestionPageState.FAILED and page.safe_error:
                return self._result_for_page(page)
            if state in {IngestionPageState.COMPLETE, IngestionPageState.EMPTY}:
                checkpoint = IngestionCheckpoint.objects.select_for_update().get(
                    company_id=page.company_id, family=page.family, flow=page.flow
                )
                expected = checkpoint.cursor if page.family == "nfe" else checkpoint.nsu
                requested = page.request_cursor if page.family == "nfe" else page.request_nsu
                if expected != requested:
                    page.state = IngestionPageState.FAILED
                    page.safe_error = "stale_checkpoint"
                    page.save(update_fields=["state", "safe_error", "updated_at"])
                    return self._result_for_page(page)
                if page.family == "nfe":
                    if page.next_cursor == requested:
                        page.state = IngestionPageState.FAILED
                        page.safe_error = "repeated_cursor"
                    else:
                        checkpoint.cursor = page.next_cursor
                        advanced = bool(page.next_cursor)
                else:
                    if page.next_nsu == requested:
                        page.state = IngestionPageState.FAILED
                        page.safe_error = "repeated_nsu"
                    else:
                        checkpoint.nsu = page.next_nsu
                        advanced = bool(page.next_nsu)
                if page.state != IngestionPageState.FAILED:
                    checkpoint.last_page = page
                    checkpoint.save(update_fields=["cursor", "nsu", "last_page", "updated_at"])
                    page.state = state
                    page.finalized_at = self.clock()
            else:
                page.state = state
                page.safe_error = _safe_reason(reason) if reason else ""
            page.save(update_fields=["state", "safe_error", "finalized_at", "updated_at"])
            self._audit(page, "advanced" if advanced else page.state, page.safe_error)
        return IngestionResult(
            page_id=page.id,
            page_state=cast(IngestionPageState, page.state),
            unit_states=tuple(unit_states),
            advanced=advanced,
            next_cursor=page.next_cursor or None,
            next_nsu=page.next_nsu or None,
            safe_reason=page.safe_error,
        )

    def _result_for_page(self, page: IngestionPage) -> IngestionResult:
        states = tuple(
            UnitOutcome(state)
            for state in page.units.order_by("first_seen_at").values_list("state", flat=True)
        )
        return IngestionResult(
            page_id=page.id,
            page_state=cast(IngestionPageState, page.state),
            unit_states=states,
            advanced=page.finalized_at is not None,
            next_cursor=page.next_cursor or None,
            next_nsu=page.next_nsu or None,
            safe_reason=page.safe_error,
        )

    def _unit_from_record(self, unit: ReceivedUnit) -> FiscalUnit:
        return FiscalUnit(
            identity=unit.identity,
            content_hash=unit.content_hash,
            kind=unit.kind,
            parent_identity=unit.parent_identity or None,
        )

    def _validate_response_position(
        self, context: IngestionContext, response: FiscalResponse
    ) -> None:
        if context.family == "nfe" and response.next_nsu is not None:
            raise IngestionPositionError("NF-e response has an NSU continuation")
        if context.family != "nfe" and response.next_cursor is not None:
            raise IngestionPositionError("ADN response has a cursor continuation")

    def _audit(self, page: IngestionPage, result: str, reason: str = "") -> None:
        AuditService().append(
            action="ingestion.page",
            entity_type="ingestion_page",
            entity_id=str(page.id),
            result=result,
            reason=reason,
            correlation_id=f"ingestion:{page.id}",
            context={
                "company_id": str(page.company_id),
                "family": page.family,
                "flow": page.flow,
                "state": page.state,
                "unit_count": page.unit_count,
            },
        )


def reconcile_ingestion(
    storage: ArtifactStorageService,
    *,
    unit_id: UUID | str | None = None,
    payload_factory: PayloadFactory = synthetic_payload,
    metadata_factory: DocumentMetadataFactory = _default_metadata,
) -> int:
    """Retry pending/failed units without deleting objects or advancing blindly."""
    return FiscalIngestionService(
        storage, payload_factory=payload_factory, metadata_factory=metadata_factory
    ).reconcile(unit_id=unit_id)


def ingest_page(
    storage: ArtifactStorageService,
    context: IngestionContext,
    response: FiscalResponse,
    *,
    payload_factory: PayloadFactory = synthetic_payload,
    metadata_factory: DocumentMetadataFactory = _default_metadata,
) -> IngestionResult:
    """Convenience port used by workers and deterministic integration tests."""
    return FiscalIngestionService(
        storage, payload_factory=payload_factory, metadata_factory=metadata_factory
    ).ingest(context, response)


def ingest_collection_response(
    storage: ArtifactStorageService,
    execution: CollectionExecution,
    response: FiscalResponse,
    *,
    flow: str = "received",
    source: str = "synthetic",
    request_cursor: str | None = None,
    request_nsu: str | None = None,
    payload_factory: PayloadFactory = synthetic_payload,
    metadata_factory: DocumentMetadataFactory = _default_metadata,
) -> IngestionResult:
    """Bridge a claimed collection execution to the durable ingestion port."""
    family = "nfe" if execution.family == "nfe" else "adn"
    result = ingest_page(
        storage,
        IngestionContext(
            company_id=execution.company_id,
            family=family,
            flow=flow,
            source=source,
            execution_ref=f"execution:{execution.id}",
            correlation_id=execution.correlation_id,
            request_cursor=request_cursor,
            request_nsu=request_nsu,
            execution_id=execution.id,
        ),
        response,
        payload_factory=payload_factory,
        metadata_factory=metadata_factory,
    )
    job = execution.job
    if job is not None:
        from nfx.collection.services import reconcile_collection_job
        from nfx.jobs.models import JobOutcomeKind

        outcome = (
            JobOutcomeKind.SUCCESS
            if result.page_state in {IngestionPageState.COMPLETE, IngestionPageState.EMPTY}
            else JobOutcomeKind.PARTIAL
            if result.page_state == IngestionPageState.PARTIAL
            else JobOutcomeKind.TEMPORARY
        )
        reconcile_collection_job(
            job,
            outcome,
            {
                "query_valid": True,
                "unit_count": len(result.unit_states),
                "next_cursor": result.next_cursor,
                "next_nsu": result.next_nsu,
                "coverage": response.coverage.value,
            },
        )
    return result
