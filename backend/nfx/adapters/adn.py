"""Semantic, simulator-only Portal Nacional/ADN distribution boundary."""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any, cast
from uuid import UUID

from nfx.adapters.simulation import (
    AdnSimulator,
    Coverage,
    FiscalAdapter,
    FiscalFamily,
    FiscalOutcome,
    FiscalRequest,
    FiscalResponse,
    FiscalUnit,
    SyntheticScenario,
    TransportCall,
)
from nfx.infrastructure.http import safe_log

logger = logging.getLogger(__name__)
_SAFE_REFERENCE = re.compile(r"^[a-z][a-z0-9_.:/-]{1,127}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_ADN_UNIT_KINDS = {"document", "event", "substitution"}


class AdnDistributionError(ValueError):
    """A request or response cannot cross the semantic ADN boundary."""


class AdnFlow(StrEnum):
    TAKEN = "taken"
    PROVIDED = "provided"
    # Portuguese aliases keep the domain vocabulary readable at call sites.
    TOMADA = "taken"
    PRESTADA = "provided"


def _flow(value: AdnFlow | str) -> AdnFlow:
    try:
        return value if isinstance(value, AdnFlow) else AdnFlow(value)
    except (TypeError, ValueError) as exc:
        raise AdnDistributionError("ADN flow is unsupported") from exc


def _reference(name: str, value: str) -> str:
    if not isinstance(value, str) or not _SAFE_REFERENCE.fullmatch(value):
        raise AdnDistributionError(f"ADN {name} is invalid")
    if re.search(
        r"https?|soap|pfx|pem|token|credential|password|secret|private|production",
        value,
        re.I,
    ):
        raise AdnDistributionError(f"ADN {name} is invalid")
    return value


def _code(value: str) -> str:
    return value if value and _SAFE_CODE.fullmatch(value) else "adn_distribution_failure"


@dataclass(frozen=True)
class AdnPosition:
    """An NSU scoped to one company actor and ADN flow."""

    actor: str
    flow: AdnFlow | str
    value: str
    family: FiscalFamily = FiscalFamily.ADN

    def __post_init__(self) -> None:
        normalized_flow = _flow(self.flow)
        if self.family != FiscalFamily.ADN:
            raise AdnDistributionError("ADN position family is invalid")
        _reference("actor", self.actor)
        _reference("NSU", self.value)
        object.__setattr__(self, "flow", normalized_flow)


@dataclass(frozen=True)
class AdnDistributionPolicy:
    """Versioned synthetic policy; official limits and layouts remain open."""

    source: str = "synthetic"
    max_page_units: int = 100
    default_page_units: int = 50
    version: str = "adn-synthetic-v1"

    def __post_init__(self) -> None:
        _reference("source", self.source)
        if (
            isinstance(self.max_page_units, bool)
            or isinstance(self.default_page_units, bool)
            or not 1 <= self.default_page_units <= self.max_page_units <= 100
        ):
            raise AdnDistributionError("ADN page policy is invalid")
        _reference("policy version", self.version)

    def validate(self, request: AdnDistributionRequest) -> None:
        if request.source != self.source:
            raise AdnDistributionError("ADN source is not allowed by policy")
        if not 1 <= request.page_limit <= self.max_page_units:
            raise AdnDistributionError("ADN page limit is out of bounds")


@dataclass(frozen=True)
class AdnDistributionRequest:
    company_id: UUID | str
    actor: str
    flow: AdnFlow | str
    source: str
    policy_reference: str
    certificate_handle: str
    correlation_id: str
    position: AdnPosition | None = None
    page_limit: int = 50
    execution_ref: str = "execution:adn-synthetic"

    def __post_init__(self) -> None:
        try:
            company_id = UUID(str(self.company_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise AdnDistributionError("ADN company reference is invalid") from exc
        normalized_flow = _flow(self.flow)
        for name, value in (
            ("actor", self.actor),
            ("source", self.source),
            ("policy reference", self.policy_reference),
            ("certificate handle", self.certificate_handle),
            ("correlation", self.correlation_id),
            ("execution", self.execution_ref),
        ):
            _reference(name, value)
        if self.position is not None and not isinstance(self.position, AdnPosition):
            raise AdnDistributionError("ADN position is invalid")
        if self.position is not None and (
            self.position.actor != self.actor or self.position.flow != normalized_flow
        ):
            raise AdnDistributionError("ADN position scope does not match request")
        if isinstance(self.page_limit, bool) or not isinstance(self.page_limit, int):
            raise AdnDistributionError("ADN page limit is invalid")
        object.__setattr__(self, "company_id", company_id)
        object.__setattr__(self, "flow", normalized_flow)


@dataclass(frozen=True)
class AdnDistributionResult:
    """Bounded semantic result; original units remain owned by P4."""

    actor: str
    flow: AdnFlow
    outcome: FiscalOutcome
    units: tuple[FiscalUnit, ...]
    continuation: AdnPosition | None
    coverage: Coverage
    consumed: int
    cooldown_until: Any | None = None
    safe_reason: str = ""
    page_limit: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, FiscalOutcome):
            raise AdnDistributionError("ADN outcome is invalid")
        if self.continuation is not None and (
            self.continuation.actor != self.actor or self.continuation.flow != self.flow
        ):
            raise AdnDistributionError("ADN continuation scope is invalid")
        if self.consumed != len(self.units) or self.consumed < 0:
            raise AdnDistributionError("ADN consumption is invalid")
        if not isinstance(self.coverage, Coverage):
            raise AdnDistributionError("ADN coverage is invalid")
        object.__setattr__(self, "safe_reason", _code(self.safe_reason))

    def as_fiscal_response(self) -> FiscalResponse:
        return FiscalResponse(
            outcome=self.outcome,
            units=self.units,
            next_nsu=self.continuation.value if self.continuation else None,
            coverage=self.coverage,
            cooldown_until=self.cooldown_until,
            error_code=(
                self.safe_reason
                if self.outcome not in {FiscalOutcome.SUCCESS, FiscalOutcome.EMPTY}
                else ""
            ),
            safe_metadata={
                "actor": self.actor,
                "flow": self.flow.value,
                "consumed": self.consumed,
                "page_limit": self.page_limit,
            },
        )


@dataclass(frozen=True)
class AdnDistributionAudit:
    event: str
    actor: str
    flow: str
    outcome: str = ""
    reason: str = ""
    nsu_prefix: str = ""
    unit_count: int = 0

    def as_dict(self) -> dict[str, str | int]:
        return {
            "event": self.event,
            "actor": self.actor,
            "flow": self.flow,
            "outcome": self.outcome,
            "reason": self.reason,
            "nsu_prefix": self.nsu_prefix,
            "unit_count": self.unit_count,
        }


@dataclass(frozen=True)
class AdnDistributionMetricsSnapshot:
    pages: int
    units: int
    cooldowns: int
    outcomes: Mapping[str, int]
    pages_by_scope: Mapping[str, int]


class AdnDistributionMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._pages = 0
        self._units = 0
        self._cooldowns = 0
        self._outcomes: Counter[str] = Counter()
        self._pages_by_scope: Counter[str] = Counter()

    def record(self, result: AdnDistributionResult) -> None:
        with self._lock:
            self._pages += 1
            self._units += result.consumed
            self._cooldowns += int(result.outcome == FiscalOutcome.COOLDOWN)
            self._outcomes[result.outcome.value] += 1
            self._pages_by_scope[f"{result.actor}:{result.flow.value}"] += 1

    def snapshot(self) -> AdnDistributionMetricsSnapshot:
        with self._lock:
            return AdnDistributionMetricsSnapshot(
                pages=self._pages,
                units=self._units,
                cooldowns=self._cooldowns,
                outcomes=dict(self._outcomes),
                pages_by_scope=dict(self._pages_by_scope),
            )


AdnAuditCallback = Callable[[Mapping[str, object]], None]
CoverageRecorder = Callable[..., object]
adn_distribution_metrics = AdnDistributionMetrics()


class AdnDistributionAdapter:
    """Interpret one synthetic ADN page and optionally hand it to P4."""

    family = FiscalFamily.ADN

    def __init__(
        self,
        transport: FiscalAdapter,
        *,
        policy: AdnDistributionPolicy | None = None,
        audit: AdnAuditCallback | None = None,
        metrics: AdnDistributionMetrics | None = None,
        coverage_recorder: CoverageRecorder | None = None,
    ) -> None:
        if getattr(transport, "family", None) != FiscalFamily.ADN:
            raise AdnDistributionError("ADN transport family is invalid")
        self.transport = transport
        self.policy = policy or AdnDistributionPolicy()
        self.audit = audit
        self.metrics = metrics or adn_distribution_metrics
        self.coverage_recorder = coverage_recorder

    def _emit(
        self,
        event: str,
        request: AdnDistributionRequest,
        *,
        result: AdnDistributionResult | None = None,
        reason: str = "",
    ) -> None:
        position = request.position.value if request.position else ""
        flow = _flow(request.flow)
        payload = AdnDistributionAudit(
            event=event,
            actor=request.actor,
            flow=flow.value,
            outcome=result.outcome.value if result else "",
            reason=_code(reason),
            nsu_prefix=position[:16],
            unit_count=result.consumed if result else 0,
        ).as_dict()
        safe_log(
            logger,
            "info",
            "adn_distribution",
            outcome=payload["outcome"] or event,
            reason=payload["reason"],
            result={
                "actor": payload["actor"],
                "flow": payload["flow"],
                "unit_count": payload["unit_count"],
            },
        )
        if self.audit is not None:
            self.audit(payload)

    def distribute(self, request: AdnDistributionRequest) -> AdnDistributionResult:
        if not isinstance(request, AdnDistributionRequest):
            raise AdnDistributionError("ADN request is invalid")
        self.policy.validate(request)
        self._emit("started", request)
        try:
            raw = self.transport.collect(
                FiscalRequest(
                    source=request.source,
                    family=FiscalFamily.ADN,
                    actor=request.actor,
                    flow=_flow(request.flow).value,
                    cursor=request.position.value if request.position else None,
                    policy_reference=request.policy_reference,
                    certificate_handle=request.certificate_handle,
                    correlation_id=request.correlation_id,
                )
            )
            result = self._interpret(request, raw)
        except AdnDistributionError:
            self._emit("rejected", request, reason="invalid_envelope")
            raise
        except Exception as exc:
            self._emit("rejected", request, reason="adapter_failure")
            raise AdnDistributionError("ADN adapter request failed") from exc
        self.metrics.record(result)
        self._emit("completed", request, result=result, reason=result.safe_reason)
        return result

    def _interpret(
        self, request: AdnDistributionRequest, raw: FiscalResponse
    ) -> AdnDistributionResult:
        if not isinstance(raw, FiscalResponse):
            raise AdnDistributionError("ADN response envelope is invalid")
        if len(raw.units) > request.page_limit:
            raise AdnDistributionError("ADN response exceeds page limit")
        if raw.next_cursor is not None:
            raise AdnDistributionError("ADN response has an unsupported cursor")
        if any(unit.kind not in _ADN_UNIT_KINDS for unit in raw.units):
            raise AdnDistributionError("ADN unit kind is unsupported")
        continuation = (
            AdnPosition(request.actor, _flow(request.flow), raw.next_nsu)
            if raw.next_nsu is not None
            else None
        )
        return AdnDistributionResult(
            actor=request.actor,
            flow=_flow(request.flow),
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
        request: AdnDistributionRequest,
        *,
        payload_factory: Callable[[FiscalUnit], Any] | None = None,
        metadata_factory: Callable[[FiscalUnit, Any], Any] | None = None,
    ) -> Any:
        """Record coverage and delegate continuation/unit ownership to P4."""
        from nfx.collection.ingestion import IngestionContext, ingest_page
        from nfx.companies.services import record_adn_coverage

        result = self.distribute(request)
        recorder = self.coverage_recorder or record_adn_coverage
        recorder(
            company_id=request.company_id,
            source=request.source,
            status=result.coverage.value,
            policy_version=self.policy.version,
            evidence_reference=f"coverage:{request.actor}:{_flow(request.flow).value}",
        )
        context = IngestionContext(
            company_id=request.company_id,
            family="adn",
            flow=f"{request.actor}:{_flow(request.flow).value}",
            source=request.source,
            execution_ref=request.execution_ref,
            correlation_id=request.correlation_id,
            request_nsu=request.position.value if request.position else None,
        )
        kwargs: dict[str, Any] = {}
        if payload_factory is not None:
            kwargs["payload_factory"] = payload_factory
        if metadata_factory is not None:
            kwargs["metadata_factory"] = metadata_factory
        else:
            from nfx.collection.ingestion import IngestionDocumentMetadata
            from nfx.documents.models import DocumentRelationship, DocumentSituation
            from nfx.documents.services import FiscalIdentity

            role = "tomada" if _flow(request.flow) == AdnFlow.TAKEN else "prestada"

            def adn_metadata(unit: FiscalUnit, _: Any) -> IngestionDocumentMetadata:
                return IngestionDocumentMetadata(
                    emitted_at=datetime.now(UTC),
                    identity=FiscalIdentity(external_id=unit.identity),
                    role=role,
                    category=unit.kind,
                    situation=DocumentSituation.UNKNOWN,
                    relationship_type=(
                        DocumentRelationship.EVENT
                        if unit.kind == "event"
                        else DocumentRelationship.SUBSTITUTION
                        if unit.kind == "substitution"
                        else None
                    ),
                )

            kwargs["metadata_factory"] = adn_metadata
        return ingest_page(storage, context, result.as_fiscal_response(), **kwargs)


class AdnDistributionSimulator:
    """Independent deterministic ADN histories for every actor and flow."""

    def __init__(
        self,
        scenario: SyntheticScenario,
        *,
        policy: AdnDistributionPolicy | None = None,
        audit: AdnAuditCallback | None = None,
        coverage_recorder: CoverageRecorder | None = None,
    ) -> None:
        if scenario.family != FiscalFamily.ADN:
            raise AdnDistributionError("ADN scenario family is invalid")
        self._metrics = AdnDistributionMetrics()
        self._replay_lock = Lock()
        self._replays: dict[tuple[str, AdnFlow, str, str], AdnDistributionResult] = {}
        self._policy = policy
        self._audit = audit
        self._coverage_recorder = coverage_recorder
        self._adapters: dict[tuple[str, AdnFlow], AdnDistributionAdapter] = {}
        self._scenario = scenario

    def _adapter(self, request: AdnDistributionRequest) -> AdnDistributionAdapter:
        key = (request.actor, _flow(request.flow))
        adapter = self._adapters.get(key)
        if adapter is None:
            adapter = AdnDistributionAdapter(
                AdnSimulator(self._scenario),
                policy=self._policy,
                audit=self._audit,
                metrics=self._metrics,
                coverage_recorder=self._coverage_recorder,
            )
            self._adapters[key] = adapter
        return adapter

    def distribute(self, request: AdnDistributionRequest) -> AdnDistributionResult:
        position = request.position.value if request.position else ""
        key = (request.actor, _flow(request.flow), position, request.correlation_id)
        with self._replay_lock:
            cached = self._replays.get(key)
            if cached is not None:
                return cached
            result = self._adapter(request).distribute(request)
            self._replays[key] = result
            return result

    def ingest(self, storage: Any, request: AdnDistributionRequest, **kwargs: Any) -> Any:
        return self._adapter(request).ingest(storage, request, **kwargs)

    def calls(self, actor: str, flow: AdnFlow | str) -> list[TransportCall]:
        transport = cast(AdnSimulator, self._adapters[(actor, _flow(flow))].transport)
        return transport.transport.calls

    def metrics_snapshot(self) -> AdnDistributionMetricsSnapshot:
        return self._metrics.snapshot()
