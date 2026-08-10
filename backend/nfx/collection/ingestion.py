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
    IngestionOutcome,
    IngestionPage,
    IngestionPageState,
    IngestionRecovery,
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
_POSITION_NUMBER = re.compile(r"(?:^|[:_-])(\d+)$")
_FAMILY = {"nfe", "adn", "nfse"}
_FAILURE_RESPONSE_OUTCOMES = {
    FiscalOutcome.NO_COVERAGE,
    FiscalOutcome.UNAVAILABLE,
    FiscalOutcome.TIMEOUT,
    FiscalOutcome.COOLDOWN,
    FiscalOutcome.BLOCKED,
    FiscalOutcome.CONFLICT,
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
    outcome: IngestionOutcome = IngestionOutcome.UNKNOWN
    recovery: IngestionRecovery = IngestionRecovery.NONE


@dataclass(frozen=True)
class IngestionClassification:
    page_state: IngestionPageState
    outcome: IngestionOutcome
    recovery: IngestionRecovery
    reason: str
    can_advance: bool


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
        relationship_type=(
            DocumentRelationship.EVENT
            if unit.kind == "event"
            else DocumentRelationship.SUBSTITUTION
            if unit.kind == "substitution"
            else None
        ),
    )


def _safe_reason(value: str) -> str:
    if value and re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", value):
        return value
    return "ingestion_failure"


def _position_number(value: str) -> int | None:
    match = _POSITION_NUMBER.search(value)
    return int(match.group(1)) if match else None


def classify_page_response(response: FiscalResponse) -> IngestionClassification:
    """Map one untrusted adapter response to the finite P4-03 contract."""
    reason = _safe_reason(response.error_code or response.outcome.value)
    if response.outcome in {FiscalOutcome.SUCCESS, FiscalOutcome.DUPLICATE}:
        state = IngestionPageState.COMPLETE if response.units else IngestionPageState.EMPTY
        return IngestionClassification(
            state,
            IngestionOutcome.SUCCESS if response.units else IngestionOutcome.VALID_EMPTY,
            IngestionRecovery.NONE,
            "" if response.units else "query_valid_empty",
            True,
        )
    if response.outcome == FiscalOutcome.EMPTY:
        return IngestionClassification(
            IngestionPageState.EMPTY,
            IngestionOutcome.VALID_EMPTY,
            IngestionRecovery.NONE,
            "query_valid_empty",
            True,
        )
    if response.outcome == FiscalOutcome.NO_COVERAGE:
        return IngestionClassification(
            IngestionPageState.NO_COVERAGE,
            IngestionOutcome.NO_COVERAGE,
            IngestionRecovery.NONE,
            reason,
            False,
        )
    if response.outcome == FiscalOutcome.UNAVAILABLE:
        return IngestionClassification(
            IngestionPageState.UNAVAILABLE,
            IngestionOutcome.UNAVAILABLE,
            IngestionRecovery.RETRY,
            reason,
            False,
        )
    if response.outcome in {FiscalOutcome.TIMEOUT, FiscalOutcome.REPEATED_CURSOR}:
        return IngestionClassification(
            IngestionPageState.RETRY,
            IngestionOutcome.TEMPORARY_FAILURE,
            IngestionRecovery.RECONCILE
            if response.outcome == FiscalOutcome.REPEATED_CURSOR
            else IngestionRecovery.RETRY,
            reason,
            False,
        )
    if response.outcome == FiscalOutcome.COOLDOWN:
        return IngestionClassification(
            IngestionPageState.COOLDOWN,
            IngestionOutcome.COOLDOWN,
            IngestionRecovery.COOLDOWN,
            reason,
            False,
        )
    if response.outcome == FiscalOutcome.BLOCKED:
        return IngestionClassification(
            IngestionPageState.BLOCKED,
            IngestionOutcome.PERMANENT_FAILURE,
            IngestionRecovery.BLOCKED,
            reason,
            False,
        )
    if response.outcome == FiscalOutcome.PARTIAL:
        return IngestionClassification(
            IngestionPageState.PARTIAL,
            IngestionOutcome.PARTIAL,
            IngestionRecovery.RETRY,
            reason,
            False,
        )
    if response.outcome == FiscalOutcome.EVENT_WITHOUT_PARENT:
        return IngestionClassification(
            IngestionPageState.FAILED,
            IngestionOutcome.QUARANTINE,
            IngestionRecovery.QUARANTINE,
            reason,
            False,
        )
    if response.outcome in {FiscalOutcome.MALFORMED, FiscalOutcome.CONFLICT}:
        return IngestionClassification(
            IngestionPageState.FAILED,
            IngestionOutcome.MALFORMED
            if response.outcome == FiscalOutcome.MALFORMED
            else IngestionOutcome.CONFLICT,
            IngestionRecovery.QUARANTINE
            if response.outcome == FiscalOutcome.MALFORMED
            else IngestionRecovery.CONFLICT_REVIEW,
            reason,
            False,
        )
    return IngestionClassification(
        IngestionPageState.FAILED,
        IngestionOutcome.UNKNOWN,
        IngestionRecovery.RECONCILE,
        "unknown_outcome",
        False,
    )


def classify_unit_treatments(unit_states: tuple[UnitOutcome, ...]) -> IngestionClassification:
    """Classify a fully processed page without weakening terminal unit semantics."""
    if any(state in {UnitOutcome.PENDING, UnitOutcome.FAILED} for state in unit_states):
        return IngestionClassification(
            IngestionPageState.PARTIAL,
            IngestionOutcome.PARTIAL,
            IngestionRecovery.RETRY,
            "unit_pending",
            False,
        )
    if UnitOutcome.CONFLICT in unit_states:
        return IngestionClassification(
            IngestionPageState.COMPLETE,
            IngestionOutcome.CONFLICT,
            IngestionRecovery.CONFLICT_REVIEW,
            "content_hash_mismatch",
            True,
        )
    if UnitOutcome.QUARANTINE in unit_states:
        return IngestionClassification(
            IngestionPageState.COMPLETE,
            IngestionOutcome.QUARANTINE,
            IngestionRecovery.QUARANTINE,
            "quarantined",
            True,
        )
    return IngestionClassification(
        IngestionPageState.COMPLETE,
        IngestionOutcome.SUCCESS,
        IngestionRecovery.NONE,
        "",
        True,
    )


def _unit_classification(treatment: UnitOutcome) -> tuple[IngestionOutcome, IngestionRecovery]:
    if treatment in {UnitOutcome.PERSISTED, UnitOutcome.REPLAY}:
        return IngestionOutcome.SUCCESS, IngestionRecovery.NONE
    if treatment == UnitOutcome.QUARANTINE:
        return IngestionOutcome.QUARANTINE, IngestionRecovery.QUARANTINE
    if treatment == UnitOutcome.CONFLICT:
        return IngestionOutcome.CONFLICT, IngestionRecovery.CONFLICT_REVIEW
    return IngestionOutcome.TEMPORARY_FAILURE, IngestionRecovery.RETRY


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
            if not self._can_resume_page(page, response):
                return self._result_for_page(page)
            self._prepare_page_retry(page, response)
            page.refresh_from_db()
        response_classification = classify_page_response(response)
        if page.state == IngestionPageState.FAILED and created:
            return self._result_for_page(page)

        if response.outcome in _FAILURE_RESPONSE_OUTCOMES:
            return self._finish_page(
                page,
                response_classification.page_state,
                [],
                response_classification.reason,
                outcome=response_classification.outcome,
                recovery=response_classification.recovery,
            )

        unit_states: list[UnitOutcome] = []
        for unit in response.units:
            received = self._register_unit(page, context, unit)
            unit_states.append(self._process_unit(received, context, unit))

        page.refresh_from_db()
        if response.outcome == FiscalOutcome.PARTIAL:
            response_classification = IngestionClassification(
                IngestionPageState.PARTIAL,
                IngestionOutcome.PARTIAL,
                IngestionRecovery.RETRY,
                "partial_response",
                False,
            )
        elif response.units:
            response_classification = classify_unit_treatments(tuple(unit_states))
        return self._finish_page(
            page,
            response_classification.page_state,
            unit_states,
            response_classification.reason,
            outcome=response_classification.outcome,
            recovery=response_classification.recovery,
        )

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
                    outcome=classify_unit_treatments(
                        tuple(UnitOutcome(state) for state in states)
                    ).outcome,
                    recovery=classify_unit_treatments(
                        tuple(UnitOutcome(state) for state in states)
                    ).recovery,
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
                    IngestionPageState.EMPTY if not page.unit_count else IngestionPageState.COMPLETE
                )
                self._finish_page(
                    page,
                    target,
                    [UnitOutcome(state) for state in states],
                    outcome=classify_unit_treatments(
                        tuple(UnitOutcome(state) for state in states)
                    ).outcome,
                    recovery=classify_unit_treatments(
                        tuple(UnitOutcome(state) for state in states)
                    ).recovery,
                )
        return repaired

    def _register_page(
        self, context: IngestionContext, response: FiscalResponse
    ) -> tuple[IngestionPage, bool]:
        page_key = (
            f"cursor:{context.request_cursor}"
            if context.request_cursor
            else (f"nsu:{context.request_nsu}" if context.request_nsu else "initial")
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
                classification = classify_page_response(response)
                safe_error = ""
                state = IngestionPageState.PENDING
                outcome = classification.outcome
                recovery = classification.recovery
                if expected != (requested or ""):
                    state = IngestionPageState.FAILED
                    safe_error = "stale_cursor" if requested else "checkpoint_position_mismatch"
                    outcome = IngestionOutcome.TEMPORARY_FAILURE
                    recovery = IngestionRecovery.RECONCILE
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
                    outcome=outcome,
                    recovery=recovery,
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

    def _can_resume_page(self, page: IngestionPage, response: FiscalResponse) -> bool:
        """Allow a changed source result only while the page is not durably complete."""
        if page.state in {IngestionPageState.COMPLETE, IngestionPageState.EMPTY}:
            return False
        if page.recovery not in {
            IngestionRecovery.RETRY,
            IngestionRecovery.RECONCILE,
            IngestionRecovery.NONE,
        }:
            return False
        return page.adapter_outcome != response.outcome.value

    def _prepare_page_retry(self, page: IngestionPage, response: FiscalResponse) -> None:
        classification = classify_page_response(response)
        IngestionPage.objects.filter(pk=page.pk).update(
            adapter_outcome=response.outcome.value,
            coverage=response.coverage.value,
            next_cursor=response.next_cursor or "",
            next_nsu=response.next_nsu or "",
            state=IngestionPageState.PENDING,
            outcome=classification.outcome,
            recovery=classification.recovery,
            safe_error="",
            unit_count=len(response.units),
            finalized_at=None,
            updated_at=self.clock(),
        )

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
            return ReceivedUnit.objects.select_for_update().get(page=page, identity=unit.identity)

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
            self._fail_unit(
                received,
                "object_unavailable",
                outcome=IngestionOutcome.UNAVAILABLE,
                recovery=IngestionRecovery.RETRY,
            )
            return UnitOutcome.FAILED

        try:
            metadata = self.metadata_factory(unit, context)
            if unit.kind in {"event", "substitution"} and metadata.parent_document_id is None:
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
                    self._finish_unit(
                        received,
                        artifact,
                        UnitOutcome.QUARANTINE,
                        "parent_missing",
                        outcome=IngestionOutcome.QUARANTINE,
                        recovery=IngestionRecovery.QUARANTINE,
                    )
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
                kind="event" if unit.kind in {"event", "substitution"} else "document",
                parent_document_id=metadata.parent_document_id,
                relationship_type=metadata.relationship_type,
            )
            persisted = persist_document(data)
        except InvalidDocumentInput:
            self._finish_unit(
                received,
                artifact,
                UnitOutcome.QUARANTINE,
                "document_input_invalid",
                outcome=IngestionOutcome.MALFORMED,
                recovery=IngestionRecovery.QUARANTINE,
            )
            return UnitOutcome.QUARANTINE
        except Exception:
            self._fail_unit(
                received,
                "document_persistence_unavailable",
                outcome=IngestionOutcome.TEMPORARY_FAILURE,
                recovery=IngestionRecovery.RETRY,
            )
            return UnitOutcome.FAILED
        outcome = UnitOutcome(persisted.status.value)
        unit_outcome, recovery = _unit_classification(outcome)
        self._finish_unit(
            received,
            artifact,
            outcome,
            persisted.reason_code or "",
            outcome=unit_outcome,
            recovery=recovery,
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
        treatment: UnitOutcome,
        reason: str = "",
        *,
        outcome: IngestionOutcome | None = None,
        recovery: IngestionRecovery = IngestionRecovery.NONE,
        document_id: UUID | None = None,
        event_id: UUID | None = None,
    ) -> None:
        now = self.clock()
        values: dict[str, object] = {
            "artifact_id": artifact.id,
            "state": treatment.value,
            "outcome": outcome or _unit_classification(treatment)[0],
            "recovery": recovery or _unit_classification(treatment)[1],
            "safe_reason": _safe_reason(reason) if reason else "",
            "terminal_at": now,
            "updated_at": now,
        }
        if document_id:
            values["document_id"] = document_id
        if event_id:
            values["event_id"] = event_id
        ReceivedUnit.objects.filter(pk=received.pk).update(**values)

    def _fail_unit(
        self,
        received: ReceivedUnit,
        reason: str,
        *,
        outcome: IngestionOutcome = IngestionOutcome.TEMPORARY_FAILURE,
        recovery: IngestionRecovery = IngestionRecovery.RETRY,
    ) -> None:
        ReceivedUnit.objects.filter(pk=received.pk).update(
            state=ReceivedUnitState.FAILED,
            outcome=outcome,
            recovery=recovery,
            safe_reason=_safe_reason(reason),
            updated_at=self.clock(),
        )

    def _finish_failed_page(self, page: IngestionPage, reason: str) -> IngestionResult:
        return self._finish_page(
            page,
            IngestionPageState.FAILED,
            [],
            reason,
            outcome=IngestionOutcome.UNKNOWN,
            recovery=IngestionRecovery.RECONCILE,
        )

    def _finish_page(
        self,
        page: IngestionPage,
        state: IngestionPageState,
        unit_states: list[UnitOutcome],
        reason: str = "",
        *,
        outcome: IngestionOutcome = IngestionOutcome.UNKNOWN,
        recovery: IngestionRecovery = IngestionRecovery.NONE,
    ) -> IngestionResult:
        advanced = False
        persisted_outcome = outcome
        persisted_recovery = recovery
        with transaction.atomic():
            page = IngestionPage.objects.select_for_update().get(pk=page.pk)
            if (
                page.state
                in {
                    IngestionPageState.FAILED,
                    IngestionPageState.NO_COVERAGE,
                    IngestionPageState.UNAVAILABLE,
                    IngestionPageState.RETRY,
                    IngestionPageState.COOLDOWN,
                    IngestionPageState.BLOCKED,
                }
                and page.safe_error
            ):
                return self._result_for_page(page)
            if state in {IngestionPageState.COMPLETE, IngestionPageState.EMPTY}:
                durable_states = tuple(page.units.values_list("state", flat=True))
                if page.unit_count != len(durable_states) or not all(
                    unit_state in INGESTION_TERMINAL_UNIT_STATES for unit_state in durable_states
                ):
                    page.state = IngestionPageState.PARTIAL
                    page.outcome = IngestionOutcome.PARTIAL
                    page.recovery = IngestionRecovery.RETRY
                    page.safe_error = "unit_pending"
                    page.save(
                        update_fields=[
                            "state",
                            "outcome",
                            "recovery",
                            "safe_error",
                            "updated_at",
                        ]
                    )
                    return self._result_for_page(page)
                checkpoint = IngestionCheckpoint.objects.select_for_update().get(
                    company_id=page.company_id, family=page.family, flow=page.flow
                )
                expected = checkpoint.cursor if page.family == "nfe" else checkpoint.nsu
                requested = page.request_cursor if page.family == "nfe" else page.request_nsu
                if expected != requested:
                    page.state = IngestionPageState.FAILED
                    persisted_outcome = IngestionOutcome.TEMPORARY_FAILURE
                    persisted_recovery = IngestionRecovery.RECONCILE
                    page.safe_error = "stale_checkpoint"
                    page.save(
                        update_fields=["state", "outcome", "recovery", "safe_error", "updated_at"]
                    )
                    return self._result_for_page(page)
                if page.family == "nfe":
                    if page.next_cursor == requested:
                        page.state = IngestionPageState.FAILED
                        persisted_outcome = IngestionOutcome.TEMPORARY_FAILURE
                        persisted_recovery = IngestionRecovery.RECONCILE
                        page.safe_error = "repeated_cursor"
                    else:
                        checkpoint.cursor = page.next_cursor
                        advanced = bool(page.next_cursor)
                else:
                    requested_number = _position_number(requested)
                    next_number = _position_number(page.next_nsu)
                    if not requested and not page.next_nsu:
                        checkpoint.last_page = page
                        checkpoint.save(update_fields=["last_page", "updated_at"])
                        page.state = state
                        page.finalized_at = self.clock()
                    elif page.next_nsu == requested:
                        page.state = IngestionPageState.FAILED
                        persisted_outcome = IngestionOutcome.TEMPORARY_FAILURE
                        persisted_recovery = IngestionRecovery.RECONCILE
                        page.safe_error = "repeated_nsu"
                    elif (
                        requested_number is not None
                        and next_number is not None
                        and next_number < requested_number
                    ):
                        page.state = IngestionPageState.FAILED
                        persisted_outcome = IngestionOutcome.TEMPORARY_FAILURE
                        persisted_recovery = IngestionRecovery.RECONCILE
                        page.safe_error = "non_monotonic_nsu"
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
            page.outcome = persisted_outcome
            page.recovery = persisted_recovery
            page.save(
                update_fields=[
                    "state",
                    "outcome",
                    "recovery",
                    "safe_error",
                    "finalized_at",
                    "updated_at",
                ]
            )
            self._audit(page, "advanced" if advanced else page.state, page.safe_error)
        return IngestionResult(
            page_id=page.id,
            page_state=cast(IngestionPageState, page.state),
            unit_states=tuple(unit_states),
            advanced=advanced,
            next_cursor=page.next_cursor or None,
            next_nsu=page.next_nsu or None,
            safe_reason=page.safe_error,
            outcome=IngestionOutcome(page.outcome),
            recovery=IngestionRecovery(page.recovery),
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
            outcome=IngestionOutcome(page.outcome),
            recovery=IngestionRecovery(page.recovery),
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
            if result.outcome in {IngestionOutcome.SUCCESS, IngestionOutcome.VALID_EMPTY}
            else JobOutcomeKind.COOLDOWN
            if result.outcome == IngestionOutcome.COOLDOWN
            else JobOutcomeKind.PERMANENT
            if result.outcome == IngestionOutcome.PERMANENT_FAILURE
            else JobOutcomeKind.PARTIAL
            if result.outcome == IngestionOutcome.PARTIAL
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
                "ingestion_outcome": result.outcome.value,
                "ingestion_recovery": result.recovery.value,
                "ingestion_reason": result.safe_reason,
            },
        )
    return result
