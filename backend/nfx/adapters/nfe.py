"""Semantic NF-e distribution boundary backed by the transport-free simulator."""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
