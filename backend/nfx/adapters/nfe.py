"""Semantic NF-e distribution boundary backed by the transport-free simulator."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ElementTree
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any, cast
from uuid import UUID

from nfx.adapters.simulation import (
    Coverage,
    FiscalAdapter,
    FiscalFamily,
    FiscalOutcome,
    FiscalRequest,
    FiscalResponse,
    FiscalUnit,
    NFeSimulator,
    SyntheticScenario,
    TransportCall,
)
from nfx.infrastructure.http import safe_log

logger = logging.getLogger(__name__)

_SAFE_REFERENCE = re.compile(r"^[a-z][a-z0-9_.:/-]{1,127}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class NFeDistributionError(ValueError):
    """A safe request or envelope cannot cross the NF-e semantic boundary."""


class NFeFlow(StrEnum):
    RECEIVED = "received"
    ISSUED = "issued"


def _flow(value: NFeFlow | str) -> NFeFlow:
    try:
        return value if isinstance(value, NFeFlow) else NFeFlow(value)
    except (TypeError, ValueError) as exc:
        raise NFeDistributionError("NF-e flow is unsupported") from exc


def _reference(name: str, value: str) -> str:
    if not isinstance(value, str) or not _SAFE_REFERENCE.fullmatch(value):
        raise NFeDistributionError(f"NF-e {name} is invalid")
    if re.search(
        r"https?|soap|pfx|pem|token|credential|password|secret|private|production",
        value,
        re.I,
    ):
        raise NFeDistributionError(f"NF-e {name} is invalid")
    return value


def _code(value: str) -> str:
    return value if value and _SAFE_CODE.fullmatch(value) else "nfe_distribution_failure"


@dataclass(frozen=True)
class NFePosition:
    """A continuation value that is explicitly scoped to one NF-e flow."""

    flow: NFeFlow | str
    value: str
    family: FiscalFamily = FiscalFamily.NFE

    def __post_init__(self) -> None:
        normalized_flow = _flow(self.flow)
        if self.family != FiscalFamily.NFE:
            raise NFeDistributionError("NF-e position family is invalid")
        _reference("position", self.value)
        object.__setattr__(self, "flow", normalized_flow)


@dataclass(frozen=True)
class NFeDistributionPolicy:
    """Versioned bounded policy; official endpoint and NSU choices stay outside this slice."""

    source: str = "synthetic"
    max_page_units: int = 100
    default_page_units: int = 50
    version: str = "nfe-synthetic-v1"

    def __post_init__(self) -> None:
        _reference("source", self.source)
        if (
            isinstance(self.max_page_units, bool)
            or isinstance(self.default_page_units, bool)
            or not 1 <= self.default_page_units <= self.max_page_units <= 100
        ):
            raise NFeDistributionError("NF-e page policy is invalid")
        _reference("policy version", self.version)

    def validate(self, request: NFeDistributionRequest) -> None:
        if request.source != self.source:
            raise NFeDistributionError("NF-e source is not allowed by policy")
        if not 1 <= request.page_limit <= self.max_page_units:
            raise NFeDistributionError("NF-e page limit is out of bounds")


@dataclass(frozen=True)
class NFeDistributionRequest:
    company_id: UUID | str
    flow: NFeFlow | str
    source: str
    actor: str
    policy_reference: str
    certificate_handle: str
    correlation_id: str
    position: NFePosition | None = None
    page_limit: int = 50
    execution_ref: str = "execution:nfe-synthetic"

    def __post_init__(self) -> None:
        try:
            company_id = UUID(str(self.company_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise NFeDistributionError("NF-e company reference is invalid") from exc
        normalized_flow = _flow(self.flow)
        for name, value in (
            ("source", self.source),
            ("actor", self.actor),
            ("policy reference", self.policy_reference),
            ("certificate handle", self.certificate_handle),
            ("correlation", self.correlation_id),
            ("execution", self.execution_ref),
        ):
            _reference(name, value)
        if self.position is not None and not isinstance(self.position, NFePosition):
            raise NFeDistributionError("NF-e position is invalid")
        if self.position is not None and self.position.flow != normalized_flow:
            raise NFeDistributionError("NF-e position flow does not match request")
        if isinstance(self.page_limit, bool) or not isinstance(self.page_limit, int):
            raise NFeDistributionError("NF-e page limit is invalid")
        object.__setattr__(self, "company_id", company_id)
        object.__setattr__(self, "flow", normalized_flow)


@dataclass(frozen=True)
class NFeDistributionResult:
    """Only bounded semantic data leaves the adapter."""

    flow: NFeFlow
    outcome: FiscalOutcome
    units: tuple[FiscalUnit, ...]
    continuation: NFePosition | None
    coverage: Coverage
    consumed: int
    cooldown_until: Any | None = None
    safe_reason: str = ""
    page_limit: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, FiscalOutcome):
            raise NFeDistributionError("NF-e outcome is invalid")
        if self.continuation is not None and self.continuation.flow != self.flow:
            raise NFeDistributionError("NF-e continuation flow is invalid")
        if self.consumed != len(self.units) or self.consumed < 0:
            raise NFeDistributionError("NF-e consumption is invalid")
        if not isinstance(self.coverage, Coverage):
            raise NFeDistributionError("NF-e coverage is invalid")
        object.__setattr__(self, "safe_reason", _code(self.safe_reason))

    def as_fiscal_response(self) -> FiscalResponse:
        return FiscalResponse(
            outcome=self.outcome,
            units=self.units,
            next_cursor=self.continuation.value if self.continuation else None,
            coverage=self.coverage,
            cooldown_until=self.cooldown_until,
            error_code=(
                self.safe_reason
                if self.outcome not in {FiscalOutcome.SUCCESS, FiscalOutcome.EMPTY}
                else ""
            ),
            safe_metadata={
                "flow": self.flow.value,
                "consumed": self.consumed,
                "page_limit": self.page_limit,
            },
        )


@dataclass(frozen=True)
class NFeDistributionAudit:
    event: str
    flow: str
    outcome: str = ""
    reason: str = ""
    cursor_prefix: str = ""
    unit_count: int = 0

    def as_dict(self) -> dict[str, str | int]:
        return {
            "event": self.event,
            "flow": self.flow,
            "outcome": self.outcome,
            "reason": self.reason,
            "cursor_prefix": self.cursor_prefix,
            "unit_count": self.unit_count,
        }


@dataclass(frozen=True)
class NFeDistributionMetricsSnapshot:
    pages: int
    units: int
    cooldowns: int
    outcomes: Mapping[str, int]
    pages_by_flow: Mapping[str, int]


class NFeDistributionMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._pages = 0
        self._units = 0
        self._cooldowns = 0
        self._outcomes: Counter[str] = Counter()
        self._pages_by_flow: Counter[str] = Counter()

    def record(self, flow: NFeFlow, result: NFeDistributionResult) -> None:
        with self._lock:
            self._pages += 1
            self._units += result.consumed
            self._cooldowns += int(result.outcome == FiscalOutcome.COOLDOWN)
            self._outcomes[result.outcome.value] += 1
            self._pages_by_flow[flow.value] += 1

    def snapshot(self) -> NFeDistributionMetricsSnapshot:
        with self._lock:
            return NFeDistributionMetricsSnapshot(
                pages=self._pages,
                units=self._units,
                cooldowns=self._cooldowns,
                outcomes=dict(self._outcomes),
                pages_by_flow=dict(self._pages_by_flow),
            )


nfe_distribution_metrics = NFeDistributionMetrics()
AuditCallback = Callable[[Mapping[str, object]], None]


class NFeDistributionAdapter:
    """Interpret one safe fiscal transport and hand pages to P4 when requested."""

    family = FiscalFamily.NFE

    def __init__(
        self,
        transport: FiscalAdapter,
        *,
        policy: NFeDistributionPolicy | None = None,
        audit: AuditCallback | None = None,
        metrics: NFeDistributionMetrics | None = None,
    ) -> None:
        if getattr(transport, "family", None) != FiscalFamily.NFE:
            raise NFeDistributionError("NF-e transport family is invalid")
        self.transport = transport
        self.policy = policy or NFeDistributionPolicy()
        self.audit = audit
        self.metrics = metrics or nfe_distribution_metrics

    def _emit(
        self,
        event: str,
        request: NFeDistributionRequest,
        *,
        result: NFeDistributionResult | None = None,
        reason: str = "",
    ) -> None:
        position = request.position.value if request.position else ""
        flow = _flow(request.flow)
        payload = NFeDistributionAudit(
            event=event,
            flow=flow.value,
            outcome=result.outcome.value if result else "",
            reason=_code(reason),
            cursor_prefix=position[:16],
            unit_count=result.consumed if result else 0,
        ).as_dict()
        safe_log(
            logger,
            "info",
            "nfe_distribution",
            outcome=payload["outcome"] or event,
            reason=payload["reason"],
            result={"flow": payload["flow"], "unit_count": payload["unit_count"]},
        )
        if self.audit is not None:
            self.audit(payload)

    def distribute(self, request: NFeDistributionRequest) -> NFeDistributionResult:
        if not isinstance(request, NFeDistributionRequest):
            raise NFeDistributionError("NF-e request is invalid")
        flow = _flow(request.flow)
        self.policy.validate(request)
        self._emit("started", request)
        try:
            raw = self.transport.collect(
                FiscalRequest(
                    source=request.source,
                    family=FiscalFamily.NFE,
                    actor=request.actor,
                    flow=flow.value,
                    cursor=request.position.value if request.position else None,
                    policy_reference=request.policy_reference,
                    certificate_handle=request.certificate_handle,
                    correlation_id=request.correlation_id,
                )
            )
            result = self._interpret(request, raw)
        except NFeDistributionError:
            self._emit("rejected", request, reason="invalid_envelope")
            raise
        except Exception as exc:
            self._emit("rejected", request, reason="adapter_failure")
            raise NFeDistributionError("NF-e adapter request failed") from exc
        self.metrics.record(flow, result)
        self._emit("completed", request, result=result, reason=result.safe_reason)
        return result

    def _interpret(
        self, request: NFeDistributionRequest, raw: FiscalResponse
    ) -> NFeDistributionResult:
        flow = _flow(request.flow)
        if not isinstance(raw, FiscalResponse):
            raise NFeDistributionError("NF-e response envelope is invalid")
        if len(raw.units) > request.page_limit:
            raise NFeDistributionError("NF-e response exceeds page limit")
        if raw.next_nsu is not None:
            raise NFeDistributionError("NF-e response has an unsupported NSU position")
        continuation = (
            NFePosition(flow, raw.next_cursor) if raw.next_cursor is not None else None
        )
        return NFeDistributionResult(
            flow=flow,
            outcome=raw.outcome,
            units=raw.units,
            continuation=continuation,
            coverage=raw.coverage,
            consumed=len(raw.units),
            cooldown_until=raw.cooldown_until,
            safe_reason=raw.error_code or raw.outcome.value,
            page_limit=request.page_limit,
        )

    def ingest(
        self,
        storage: Any,
        request: NFeDistributionRequest,
        *,
        payload_factory: Callable[[FiscalUnit], Any] | None = None,
        metadata_factory: Callable[[FiscalUnit, Any], Any] | None = None,
    ) -> Any:
        """Use the single P4 page/unit/checkpoint owner after distribution interpretation."""
        from nfx.collection.ingestion import IngestionContext, ingest_page

        result = self.distribute(request)
        flow = _flow(request.flow)
        context = IngestionContext(
            company_id=request.company_id,
            family="nfe",
            flow=flow.value,
            source=request.source,
            execution_ref=request.execution_ref,
            correlation_id=request.correlation_id,
            request_cursor=request.position.value if request.position else None,
        )
        kwargs: dict[str, Any] = {}
        if payload_factory is not None:
            kwargs["payload_factory"] = payload_factory
        if metadata_factory is not None:
            kwargs["metadata_factory"] = metadata_factory
        return ingest_page(storage, context, result.as_fiscal_response(), **kwargs)


class NFeDistributionSimulator:
    """Two independent deterministic NF-e adapter histories over one scenario."""

    def __init__(
        self,
        scenario: SyntheticScenario,
        *,
        policy: NFeDistributionPolicy | None = None,
        audit: AuditCallback | None = None,
    ) -> None:
        if scenario.family != FiscalFamily.NFE:
            raise NFeDistributionError("NF-e scenario family is invalid")
        self._metrics = NFeDistributionMetrics()
        self._replay_lock = Lock()
        self._replays: dict[tuple[NFeFlow, str, str], NFeDistributionResult] = {}
        self._adapters = {
            flow: NFeDistributionAdapter(
                NFeSimulator(scenario), policy=policy, audit=audit, metrics=self._metrics
            )
            for flow in NFeFlow
        }

    def distribute(self, request: NFeDistributionRequest) -> NFeDistributionResult:
        flow = _flow(request.flow)
        position = request.position.value if request.position else ""
        replay_key = (flow, position, request.correlation_id)
        with self._replay_lock:
            cached = self._replays.get(replay_key)
            if cached is not None:
                return cached
            result = self._adapters[flow].distribute(request)
            self._replays[replay_key] = result
            return result

    def ingest(self, storage: Any, request: NFeDistributionRequest, **kwargs: Any) -> Any:
        return self._adapters[_flow(request.flow)].ingest(storage, request, **kwargs)

    def calls(self, flow: NFeFlow | str) -> list[TransportCall]:
        transport = cast(NFeSimulator, self._adapters[_flow(flow)].transport)
        return transport.transport.calls

    def metrics_snapshot(self) -> NFeDistributionMetricsSnapshot:
        return self._metrics.snapshot()


class NFeFollowUpError(ValueError):
    """A safe NF-e follow-up request or response cannot cross the adapter boundary."""


class NFeFollowUpOutcome(StrEnum):
    PERMITTED = "permitted"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    RETRY = "retry"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"
    MALFORMED = "malformed"
    UNKNOWN = "unknown"


class NFeFollowUpScenarioName(StrEnum):
    PERMITTED = "permitted"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"
    MALFORMED = "malformed"
    UNKNOWN = "unknown"
    EVENT_WITH_PARENT = "event_with_parent"
    EVENT_WITHOUT_PARENT = "event_without_parent"
    EVENT_CONFLICT = "event_conflict"


_FOLLOWUP_REFERENCE = re.compile(r"^[a-z][a-z0-9_.:/-]{1,127}$")
_MAX_FOLLOWUP_PAYLOAD = 10 * 1024 * 1024
_XML_CONTENT_TYPES = frozenset({"application/xml", "text/xml"})


def _document_id(value: UUID | str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise NFeFollowUpError("NF-e document reference is invalid") from exc


def _followup_reference(name: str, value: str) -> str:
    if not isinstance(value, str) or not _FOLLOWUP_REFERENCE.fullmatch(value):
        raise NFeFollowUpError(f"NF-e {name} is invalid")
    if re.search(
        r"https?|soap|pfx|pem|token|credential|password|secret|private|production",
        value,
        re.I,
    ):
        raise NFeFollowUpError(f"NF-e {name} is invalid")
    return value


@dataclass(frozen=True)
class NFeScienceRequest:
    company_id: UUID | str
    document_id: UUID | str
    flow: NFeFlow | str
    source: str
    actor: str
    policy_reference: str
    certificate_handle: str
    correlation_id: str
    intent: str = "science_of_operation"

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_id", _document_id(self.company_id))
        object.__setattr__(self, "document_id", _document_id(self.document_id))
        object.__setattr__(self, "flow", _flow(self.flow))
        for name, value in (
            ("source", self.source),
            ("actor", self.actor),
            ("policy reference", self.policy_reference),
            ("certificate handle", self.certificate_handle),
            ("correlation", self.correlation_id),
            ("intent", self.intent),
        ):
            _followup_reference(name, value)


@dataclass(frozen=True)
class NFeScienceResult:
    document_id: UUID
    flow: NFeFlow
    outcome: FiscalOutcome
    retrieval_permitted: bool
    correlation_id: str
    safe_reason: str = ""
    cooldown_until: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, UUID) or not isinstance(self.flow, NFeFlow):
            raise NFeFollowUpError("NF-e Ciência identity is invalid")
        if not isinstance(self.outcome, FiscalOutcome):
            raise NFeFollowUpError("NF-e Ciência outcome is invalid")
        _followup_reference("correlation", self.correlation_id)
        if self.retrieval_permitted and self.outcome != FiscalOutcome.SUCCESS:
            raise NFeFollowUpError("NF-e Ciência permission is inconsistent")
        object.__setattr__(self, "safe_reason", _code(self.safe_reason or self.outcome.value))

    def as_job_outcome(self) -> Any:
        from nfx.jobs.handlers import HandlerOutcome

        result = {
            "document_id": str(self.document_id),
            "flow": self.flow.value,
            "outcome": self.outcome.value,
            "retrieval_permitted": self.retrieval_permitted,
        }
        if self.outcome == FiscalOutcome.SUCCESS:
            return HandlerOutcome.success(result)
        if self.outcome == FiscalOutcome.COOLDOWN:
            return HandlerOutcome.cooldown(
                cooldown_until=self.cooldown_until,
                error_code=self.safe_reason,
                result=result,
            )
        if self.outcome in {FiscalOutcome.UNAVAILABLE, FiscalOutcome.TIMEOUT}:
            return HandlerOutcome.temporary(error_code=self.safe_reason, result=result)
        if self.outcome == FiscalOutcome.BLOCKED:
            return HandlerOutcome.permanent(error_code=self.safe_reason, result=result)
        return HandlerOutcome.partial(error_code=self.safe_reason, result=result)


@dataclass(frozen=True)
class NFeCompleteXmlRequest:
    company_id: UUID | str
    document_id: UUID | str
    flow: NFeFlow | str
    source: str
    actor: str
    policy_reference: str
    certificate_handle: str
    correlation_id: str
    science_correlation_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_id", _document_id(self.company_id))
        object.__setattr__(self, "document_id", _document_id(self.document_id))
        object.__setattr__(self, "flow", _flow(self.flow))
        for name, value in (
            ("source", self.source),
            ("actor", self.actor),
            ("policy reference", self.policy_reference),
            ("certificate handle", self.certificate_handle),
            ("correlation", self.correlation_id),
            ("science correlation", self.science_correlation_id),
        ):
            _followup_reference(name, value)


@dataclass(frozen=True)
class NFeCompleteXmlResponse:
    original_payload: bytes
    xml_payload: bytes
    content_type: str = "application/xml"
    original_content_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        if not isinstance(self.original_payload, bytes) or not isinstance(self.xml_payload, bytes):
            raise NFeFollowUpError("NF-e complete XML payload is invalid")
        if not 1 <= len(self.original_payload) <= _MAX_FOLLOWUP_PAYLOAD:
            raise NFeFollowUpError("NF-e original response exceeds its limit")
        if not 1 <= len(self.xml_payload) <= _MAX_FOLLOWUP_PAYLOAD:
            raise NFeFollowUpError("NF-e XML exceeds its limit")
        if self.content_type not in _XML_CONTENT_TYPES:
            raise NFeFollowUpError("NF-e XML content type is invalid")
        if self.original_content_type != "application/octet-stream":
            raise NFeFollowUpError("NF-e original content type is invalid")


@dataclass(frozen=True)
class NFeEventRequest:
    company_id: UUID | str
    parent_document_id: UUID | str
    flow: NFeFlow | str
    source: str
    actor: str
    policy_reference: str
    certificate_handle: str
    correlation_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "company_id", _document_id(self.company_id))
        object.__setattr__(self, "parent_document_id", _document_id(self.parent_document_id))
        object.__setattr__(self, "flow", _flow(self.flow))
        for name, value in (
            ("source", self.source),
            ("actor", self.actor),
            ("policy reference", self.policy_reference),
            ("certificate handle", self.certificate_handle),
            ("correlation", self.correlation_id),
        ):
            _followup_reference(name, value)


@dataclass(frozen=True)
class NFeFollowUpScenario:
    name: NFeFollowUpScenarioName
    science_outcome: FiscalOutcome
    retrieval_permitted: bool
    complete_xml: NFeCompleteXmlResponse | None
    event_response: FiscalResponse

    def __post_init__(self) -> None:
        if self.retrieval_permitted != (self.science_outcome == FiscalOutcome.SUCCESS):
            raise NFeFollowUpError("NF-e follow-up scenario permission is inconsistent")
        if self.retrieval_permitted and self.complete_xml is None:
            raise NFeFollowUpError("permitted scenario must provide complete XML")
        if self.event_response.next_cursor is not None or self.event_response.next_nsu is not None:
            raise NFeFollowUpError("NF-e event response cannot advance distribution position")


@dataclass(frozen=True)
class NFeFollowUpCall:
    operation: str
    flow: NFeFlow
    correlation_id: str


def _followup_unit(
    seed: int, label: str, *, kind: str = "event", parent: str | None = None
) -> FiscalUnit:
    identity = f"synthetic:nfe:{seed}:{label}"
    digest = __import__("hashlib").sha256(
        f"nfx-synthetic-unit:{identity}".encode()
    ).hexdigest()
    return FiscalUnit(
        identity=identity,
        content_hash=digest,
        kind=kind,
        parent_identity=parent,
        occurred_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )


def build_nfe_followup_scenario(
    name: NFeFollowUpScenarioName | str, *, seed: int
) -> NFeFollowUpScenario:
    try:
        selected = (
            name
            if isinstance(name, NFeFollowUpScenarioName)
            else NFeFollowUpScenarioName(name)
        )
    except (TypeError, ValueError) as exc:
        raise NFeFollowUpError("unknown NF-e follow-up scenario") from exc
    if not isinstance(seed, int) or seed < 0:
        raise NFeFollowUpError("NF-e follow-up seed is invalid")
    successful = selected in {
        NFeFollowUpScenarioName.PERMITTED,
        NFeFollowUpScenarioName.EVENT_WITH_PARENT,
        NFeFollowUpScenarioName.EVENT_WITHOUT_PARENT,
        NFeFollowUpScenarioName.EVENT_CONFLICT,
    }
    outcomes = {
        NFeFollowUpScenarioName.DENIED: FiscalOutcome.BLOCKED,
        NFeFollowUpScenarioName.UNAVAILABLE: FiscalOutcome.UNAVAILABLE,
        NFeFollowUpScenarioName.TIMEOUT: FiscalOutcome.TIMEOUT,
        NFeFollowUpScenarioName.COOLDOWN: FiscalOutcome.COOLDOWN,
        NFeFollowUpScenarioName.BLOCKED: FiscalOutcome.BLOCKED,
        NFeFollowUpScenarioName.MALFORMED: FiscalOutcome.MALFORMED,
        NFeFollowUpScenarioName.UNKNOWN: FiscalOutcome.UNKNOWN,
    }
    science_outcome = FiscalOutcome.SUCCESS if successful else outcomes[selected]
    xml = (
        NFeCompleteXmlResponse(
            original_payload=f"synthetic-nfe-original:{seed}".encode(),
            xml_payload=b"<nfeProc><synthetic>nfe</synthetic></nfeProc>",
        )
        if successful
        else None
    )
    event_units: tuple[FiscalUnit, ...] = ()
    if selected == NFeFollowUpScenarioName.EVENT_WITH_PARENT:
        event_units = (_followup_unit(seed, "event", parent=f"synthetic:nfe:{seed}:first"),)
    elif selected == NFeFollowUpScenarioName.EVENT_WITHOUT_PARENT:
        event_units = (_followup_unit(seed, "event", parent=f"synthetic:nfe:{seed}:missing"),)
    elif selected == NFeFollowUpScenarioName.EVENT_CONFLICT:
        event_units = (
            _followup_unit(seed, "event-conflict", parent=f"synthetic:nfe:{seed}:first"),
        )
    return NFeFollowUpScenario(
        name=selected,
        science_outcome=science_outcome,
        retrieval_permitted=successful,
        complete_xml=xml,
        event_response=FiscalResponse(
            FiscalOutcome.SUCCESS if event_units else FiscalOutcome.EMPTY,
            units=event_units,
            safe_metadata={"generated": True},
        ),
    )


class NFeFollowUpSimulator:
    """Deterministic Ciência/XML/event transport with no network capability."""

    family = FiscalFamily.NFE

    def __init__(self, scenario: NFeFollowUpScenario) -> None:
        self.scenario = scenario
        self._lock = Lock()
        self._science: dict[tuple[UUID, NFeFlow, str], NFeScienceResult] = {}
        self._xml: dict[tuple[UUID, NFeFlow, str], NFeCompleteXmlResponse] = {}
        self._events: dict[tuple[NFeFlow, str], FiscalResponse] = {}
        self._calls: list[NFeFollowUpCall] = []

    def science(self, request: NFeScienceRequest) -> NFeScienceResult:
        document_id = UUID(str(request.document_id))
        flow = _flow(request.flow)
        key = (document_id, flow, request.correlation_id)
        with self._lock:
            if key not in self._science:
                result = NFeScienceResult(
                    document_id=document_id,
                    flow=flow,
                    outcome=self.scenario.science_outcome,
                    retrieval_permitted=self.scenario.retrieval_permitted,
                    correlation_id=request.correlation_id,
                    safe_reason=self.scenario.science_outcome.value,
                    cooldown_until=(
                        datetime(2030, 1, 1, tzinfo=UTC)
                        if self.scenario.science_outcome == FiscalOutcome.COOLDOWN
                        else None
                    ),
                )
                self._science[key] = result
                self._calls.append(NFeFollowUpCall("science", flow, request.correlation_id))
            return self._science[key]

    def complete_xml(self, request: NFeCompleteXmlRequest) -> NFeCompleteXmlResponse:
        flow = _flow(request.flow)
        key = (UUID(str(request.document_id)), flow, request.science_correlation_id)
        with self._lock:
            if key not in self._science or not self._science[key].retrieval_permitted:
                raise NFeFollowUpError("complete XML requires permitted Ciência")
            if self.scenario.complete_xml is None:
                raise NFeFollowUpError("complete XML is unavailable")
            if key not in self._xml:
                self._xml[key] = self.scenario.complete_xml
                self._calls.append(
                    NFeFollowUpCall("complete_xml", flow, request.correlation_id)
                )
            return self._xml[key]

    def events(self, request: NFeEventRequest) -> FiscalResponse:
        flow = _flow(request.flow)
        key = (flow, request.correlation_id)
        with self._lock:
            if key not in self._events:
                self._events[key] = self.scenario.event_response
                self._calls.append(NFeFollowUpCall("events", flow, request.correlation_id))
            return self._events[key]

    def calls(self) -> tuple[NFeFollowUpCall, ...]:
        with self._lock:
            return tuple(self._calls)


class NFeFollowUpAdapter:
    """Validate follow-up semantics and keep permission state at the adapter edge."""

    def __init__(
        self, transport: NFeFollowUpSimulator, *, audit: AuditCallback | None = None
    ) -> None:
        if getattr(transport, "family", None) != FiscalFamily.NFE:
            raise NFeFollowUpError("NF-e follow-up transport family is invalid")
        self.transport = transport
        self.audit = audit

    def _audit(self, event: str, flow: NFeFlow, outcome: str = "", reason: str = "") -> None:
        payload = {
            "event": event,
            "flow": flow.value,
            "outcome": outcome,
            "reason": _code(reason),
        }
        safe_log(
            logger,
            "info",
            "nfe_followup",
            outcome=outcome or event,
            reason=payload["reason"],
            result={"flow": flow.value},
        )
        if self.audit is not None:
            self.audit(payload)

    def science(self, request: NFeScienceRequest) -> NFeScienceResult:
        if not isinstance(request, NFeScienceRequest):
            raise NFeFollowUpError("NF-e Ciência request is invalid")
        flow = _flow(request.flow)
        self._audit("science_started", flow)
        result = self.transport.science(request)
        if result.document_id != UUID(str(request.document_id)) or result.flow != flow:
            raise NFeFollowUpError("NF-e Ciência identity is inconsistent")
        self._audit("science_completed", flow, result.outcome.value, result.safe_reason)
        return result

    def complete_xml(self, request: NFeCompleteXmlRequest) -> NFeCompleteXmlResponse:
        if not isinstance(request, NFeCompleteXmlRequest):
            raise NFeFollowUpError("NF-e complete XML request is invalid")
        flow = _flow(request.flow)
        response = self.transport.complete_xml(request)
        self._audit("xml_completed", flow, FiscalOutcome.SUCCESS.value)
        return response

    def events(self, request: NFeEventRequest) -> FiscalResponse:
        if not isinstance(request, NFeEventRequest):
            raise NFeFollowUpError("NF-e event request is invalid")
        flow = _flow(request.flow)
        response = self.transport.events(request)
        if not isinstance(response, FiscalResponse):
            raise NFeFollowUpError("NF-e event response envelope is invalid")
        self._audit("events_completed", flow, response.outcome.value)
        return response


def _validate_followup_xml(response: NFeCompleteXmlResponse) -> None:
    if any(
        marker in response.xml_payload.upper()
        for marker in (b"<!DOCTYPE", b"<!ENTITY", b"SYSTEM", b"PUBLIC")
    ):
        raise NFeFollowUpError("NF-e XML parser rejected unsafe declarations")
    try:
        root = ElementTree.fromstring(response.xml_payload)
    except (ElementTree.ParseError, ValueError) as exc:
        raise NFeFollowUpError("NF-e XML is malformed") from exc
    if root.tag.rsplit("}", 1)[-1] not in {"nfeProc", "NFe", "procNFe"}:
        raise NFeFollowUpError("NF-e XML root is unsupported")


def _ensure_followup_artifact(
    storage: Any,
    logical_class: str,
    logical_key: str,
    content_type: str,
    payload: bytes,
) -> Any:
    from nfx.artifacts.models import Artifact, ArtifactState

    existing = Artifact.objects.filter(logical_key=logical_key).order_by("created_at").first()
    if existing is None:
        try:
            existing = storage.begin(logical_class, logical_key, content_type)
        except Exception:
            existing = (
                Artifact.objects.filter(logical_key=logical_key)
                .order_by("created_at")
                .first()
            )
            if existing is None:
                raise NFeFollowUpError("NF-e evidence registration failed")
    if existing is None:
        raise NFeFollowUpError("NF-e evidence registration failed")
    artifact = existing
    if artifact.state != ArtifactState.FINALIZED:
        try:
            artifact = storage.transmit(artifact.id, (payload,))
        except Exception:
            artifact.refresh_from_db()
            if artifact.state != ArtifactState.FINALIZED:
                raise NFeFollowUpError("NF-e evidence storage failed")
    if artifact.digest != __import__("hashlib").sha256(payload).hexdigest():
        raise NFeFollowUpError("NF-e evidence integrity conflict")
    return artifact


class NFeFollowUpService:
    """Authorization, job handoff, and P4-owned persistence for P5-02."""

    def __init__(self, adapter: NFeFollowUpAdapter, storage: Any | None = None) -> None:
        self.adapter = adapter
        self.storage = storage

    @classmethod
    def from_runtime(cls) -> NFeFollowUpService:
        scenario = build_nfe_followup_scenario("permitted", seed=1)
        return cls(NFeFollowUpAdapter(NFeFollowUpSimulator(scenario)))

    @staticmethod
    def _validate_document_context(
        request: NFeScienceRequest | NFeCompleteXmlRequest | NFeEventRequest,
    ) -> None:
        from nfx.certificates.models import Certificate, CertificateState
        from nfx.certificates.services import certificate_status
        from nfx.companies.models import Company, CompanyStatus
        from nfx.documents.models import Document, DocumentFamily

        if not Company.objects.filter(id=request.company_id, status=CompanyStatus.ACTIVE).exists():
            raise NFeFollowUpError("company is inactive")
        target_document_id = (
            request.document_id
            if hasattr(request, "document_id")
            else request.parent_document_id
        )
        if not Document.objects.filter(
            id=target_document_id,
            company_id=request.company_id,
            family=DocumentFamily.NFE,
            flow=_flow(request.flow).value,
        ).exists():
            raise NFeFollowUpError("NF-e document is unavailable")
        certificate = Certificate.objects.filter(
            company_id=request.company_id, state=CertificateState.CURRENT
        ).order_by("-activated_at").first()
        if certificate is None or certificate_status(certificate) not in {
            "valido",
            "proximo_vencimento",
        }:
            raise NFeFollowUpError("certificate is unavailable")

    def enqueue_science(
        self, request: NFeScienceRequest, actor: Any, *, policy: Any = None
    ) -> Any:
        from django.utils import timezone

        from nfx.identity.models import Role
        from nfx.identity.policy import Action, authorize
        from nfx.jobs.policy import select_policy
        from nfx.jobs.services import JobEngine

        if actor is None or not authorize(
            actor.role, Action.CONTROL_COLLECTIONS, actor_id=actor.user_id
        ):
            raise NFeFollowUpError("follow-up control access required")
        if actor.role not in Role.values:
            raise NFeFollowUpError("actor is invalid")
        self._validate_document_context(request)
        now = timezone.now()
        effective_policy = policy or select_policy(source=request.source, flow="nfe", at=now)
        return JobEngine().enqueue(
            job_type="nfe.science",
            logical_target=f"document:{request.document_id}",
            payload={
                "operation": "science",
                "company_id": str(request.company_id),
                "document_id": str(request.document_id),
                "flow": _flow(request.flow).value,
                "source": request.source,
                "actor": request.actor,
                "actor_id": actor.user_id,
                "policy_reference": request.policy_reference,
                "certificate_handle": request.certificate_handle,
                "correlation_id": request.correlation_id,
                "intent": request.intent,
            },
            idempotency_key=f"nfe:science:{request.document_id}:{request.intent}:{request.correlation_id}",
            scheduled_at=now,
            policy=effective_policy,
        )

    def handle_science_job(self, job: Any) -> Any:
        from nfx.jobs.handlers import HandlerOutcome
        from nfx.jobs.services import JobEngine

        payload = job.payload
        request = NFeScienceRequest(
            company_id=payload["company_id"],
            document_id=payload["document_id"],
            flow=payload["flow"],
            source=payload["source"],
            actor=payload["actor"],
            policy_reference=payload["policy_reference"],
            certificate_handle=payload["certificate_handle"],
            correlation_id=payload["correlation_id"],
            intent=payload["intent"],
        )
        try:
            self._validate_document_context(request)
            result = self.adapter.science(request)
        except NFeFollowUpError:
            return HandlerOutcome.permanent(error_code="followup_rejected")
        classified = result.as_job_outcome()
        if result.retrieval_permitted and classified.kind == "success":
            xml_request = NFeCompleteXmlRequest(
                company_id=request.company_id,
                document_id=request.document_id,
                flow=request.flow,
                source=request.source,
                actor=request.actor,
                policy_reference=request.policy_reference,
                certificate_handle=request.certificate_handle,
                correlation_id=f"xml:{request.correlation_id}",
                science_correlation_id=request.correlation_id,
            )
            xml_job = JobEngine().enqueue(
                job_type="nfe.complete_xml",
                logical_target=f"document:{request.document_id}",
                payload={
                    "operation": "complete_xml",
                    "company_id": str(xml_request.company_id),
                    "document_id": str(xml_request.document_id),
                    "flow": _flow(xml_request.flow).value,
                    "source": xml_request.source,
                    "actor": xml_request.actor,
                    "policy_reference": xml_request.policy_reference,
                    "certificate_handle": xml_request.certificate_handle,
                    "correlation_id": xml_request.correlation_id,
                    "science_correlation_id": xml_request.science_correlation_id,
                    "science_job_id": str(job.id),
                },
                idempotency_key=f"nfe:xml:{request.document_id}:{request.correlation_id}",
                policy=job.effective_policy,
            )
            return HandlerOutcome.success({**classified.result, "followup_job_id": str(xml_job.id)})
        return classified

    def handle_xml_job(self, job: Any) -> Any:
        from nfx.jobs.handlers import HandlerOutcome
        from nfx.jobs.models import Job, JobState

        payload = job.payload
        science = Job.objects.filter(id=payload["science_job_id"], state=JobState.COMPLETED).first()
        if science is None or not (science.safe_result or {}).get("retrieval_permitted"):
            return HandlerOutcome.permanent(error_code="science_required")
        request = NFeCompleteXmlRequest(
            company_id=payload["company_id"],
            document_id=payload["document_id"],
            flow=payload["flow"],
            source=payload["source"],
            actor=payload["actor"],
            policy_reference=payload["policy_reference"],
            certificate_handle=payload["certificate_handle"],
            correlation_id=payload["correlation_id"],
            science_correlation_id=payload["science_correlation_id"],
        )
        try:
            self._validate_document_context(request)
            response = self.adapter.complete_xml(request)
            if self.storage is None:
                from nfx.artifacts.storage import (
                    ArtifactStorageService,
                    object_store_from_environment,
                )

                object_store: Any = object_store_from_environment()
                storage: Any = ArtifactStorageService(object_store)
            else:
                storage = self.storage
            from nfx.documents.services import attach_document_evidence

            original = _ensure_followup_artifact(
                storage,
                "fiscal_original",
                f"nfe:{request.document_id}:original:{request.science_correlation_id}",
                response.original_content_type,
                response.original_payload,
            )
            attach_document_evidence(request.document_id, original.id)
            _validate_followup_xml(response)
            xml = _ensure_followup_artifact(
                storage,
                "fiscal_xml",
                f"nfe:{request.document_id}:xml:{request.science_correlation_id}",
                response.content_type,
                response.xml_payload,
            )
            evidence = attach_document_evidence(request.document_id, xml.id)
            return HandlerOutcome.success(
                {
                    "document_id": str(request.document_id),
                    "complete_evidence_id": str(evidence.evidence_id),
                    "original_evidence_id": str(original.id),
                }
            )
        except NFeFollowUpError:
            return HandlerOutcome.permanent(error_code="xml_rejected")

    def ingest_events(self, storage: Any, request: NFeEventRequest) -> Any:
        from nfx.collection.ingestion import (
            IngestionContext,
            IngestionDocumentMetadata,
            ingest_page,
            synthetic_payload,
        )
        from nfx.documents.services import FiscalIdentity

        self._validate_document_context(request)
        response = self.adapter.events(request)
        def metadata(unit: FiscalUnit, _context: Any) -> IngestionDocumentMetadata:
            return IngestionDocumentMetadata(
                emitted_at=unit.occurred_at or datetime.now(UTC),
                identity=FiscalIdentity(external_id=unit.identity),
                role="evento",
                category="substituicao" if unit.kind == "substitution" else "evento",
                relationship_type="substitution" if unit.kind == "substitution" else "event",
            )
        context = IngestionContext(
            company_id=request.company_id,
            family="nfe",
            flow=f"{_flow(request.flow).value}:followup",
            document_flow=_flow(request.flow).value,
            page_key=f"followup:{request.correlation_id}",
            source=request.source,
            execution_ref=f"execution:{request.correlation_id}",
            correlation_id=request.correlation_id,
        )
        return ingest_page(
            storage,
            context,
            response,
            payload_factory=synthetic_payload,
            metadata_factory=metadata,
        )


def ensure_nfe_followup_handler(service: NFeFollowUpService | None = None) -> None:
    from nfx.jobs.handlers import register_handler

    configured = service or NFeFollowUpService.from_runtime()
    register_handler("nfe.science", configured.handle_science_job)
    register_handler("nfe.complete_xml", configured.handle_xml_job)
