"""Deterministic, transport-free fiscal adapter ports and synthetic fixtures."""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

_SAFE_REFERENCE = re.compile(r"^[a-z][a-z0-9_.:/-]{1,127}$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_REFERENCE = re.compile(
    r"(?:https?|soap|pfx|pem|token|credential|password|secret|private|production)", re.I
)
_FORBIDDEN_METADATA = re.compile(
    r"(?:xml|pdf|pfx|pem|token|credential|password|secret|private|content|payload)", re.I
)


class ScenarioValidationError(ValueError):
    """A generated scenario is invalid and must not be interpreted as empty."""


class ScenarioExecutionError(RuntimeError):
    """A simulator request does not match the declared scenario sequence."""


class FiscalFamily(StrEnum):
    NFE = "nfe"
    ADN = "adn"


class FiscalOutcome(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    NO_COVERAGE = "no_coverage"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    COOLDOWN = "cooldown"
    BLOCKED = "blocked"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    MALFORMED = "malformed"
    EVENT_WITHOUT_PARENT = "event_without_parent"
    REPEATED_CURSOR = "repeated_cursor"


class Coverage(StrEnum):
    AVAILABLE = "available"
    NONE = "none"
    UNKNOWN = "unknown"


class ScenarioName(StrEnum):
    PAGINATED_SUCCESS = "paginated_success"
    VALID_EMPTY = "valid_empty"
    NO_COVERAGE = "no_coverage"
    DUPLICATE_EQUAL_HASH = "duplicate_equal_hash"
    IDENTITY_CONFLICT = "identity_conflict"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    COOLDOWN = "cooldown"
    PERMANENT_BLOCK = "permanent_block"
    MALFORMED_PAYLOAD = "malformed_payload"
    EVENT_WITHOUT_PARENT = "event_without_parent"
    REPEATED_CURSOR = "repeated_cursor"
    PARTIAL_RESULT = "partial_result"
    INTERRUPTION_RESTART = "interruption_restart"


def _reference(field_name: str, value: str, *, required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value):
        raise ValueError(f"{field_name} must be a safe reference")
    if not value:
        return value
    if not _SAFE_REFERENCE.fullmatch(value) or _FORBIDDEN_REFERENCE.search(value):
        raise ValueError(f"{field_name} must be a safe reference")
    return value


def _code(value: str) -> str:
    if not _SAFE_CODE.fullmatch(value):
        raise ScenarioValidationError("scenario error code is unsafe")
    return value


@dataclass(frozen=True)
class FiscalRequest:
    """Safe context passed to a future fiscal adapter implementation."""

    source: str
    family: FiscalFamily
    actor: str
    flow: str
    cursor: str | None
    policy_reference: str
    certificate_handle: str
    correlation_id: str

    def __post_init__(self) -> None:
        _reference("source", self.source)
        if not isinstance(self.family, FiscalFamily):
            raise ValueError("family must be a supported fiscal family")
        _reference("actor", self.actor)
        _reference("flow", self.flow)
        if self.cursor is not None:
            _reference("cursor", self.cursor)
        _reference("policy_reference", self.policy_reference)
        _reference("certificate_handle", self.certificate_handle)
        _reference("correlation_id", self.correlation_id)


@dataclass(frozen=True)
class FiscalUnit:
    """Synthetic identity and hash references; no fiscal content is carried."""

    identity: str
    content_hash: str
    kind: str = "document"
    parent_identity: str | None = None
    synthetic: bool = True

    def __post_init__(self) -> None:
        _reference("identity", self.identity)
        if not _HASH.fullmatch(self.content_hash):
            raise ScenarioValidationError("synthetic unit hash is invalid")
        _code(self.kind)
        if self.parent_identity is not None:
            _reference("parent_identity", self.parent_identity)
        if not self.synthetic:
            raise ScenarioValidationError("only generated synthetic units are supported")


@dataclass(frozen=True)
class FiscalResponse:
    """Typed adapter response containing only safe references and metadata."""

    outcome: FiscalOutcome
    units: tuple[FiscalUnit, ...] = ()
    next_cursor: str | None = None
    next_nsu: str | None = None
    coverage: Coverage = Coverage.AVAILABLE
    cooldown_until: datetime | None = None
    error_code: str = ""
    safe_metadata: Mapping[str, bool | int | str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, FiscalOutcome):
            raise ScenarioValidationError("response outcome is invalid")
        if self.next_cursor is not None:
            _reference("next_cursor", self.next_cursor)
        if self.next_nsu is not None:
            _reference("next_nsu", self.next_nsu)
        if self.next_cursor is not None and self.next_nsu is not None:
            raise ScenarioValidationError("response cannot contain both cursor and NSU")
        if not isinstance(self.coverage, Coverage):
            raise ScenarioValidationError("response coverage is invalid")
        if self.cooldown_until is not None and (
            self.cooldown_until.tzinfo is None or self.cooldown_until.utcoffset() is None
        ):
            raise ScenarioValidationError("cooldown must be timezone-aware")
        if self.outcome == FiscalOutcome.COOLDOWN and self.cooldown_until is None:
            raise ScenarioValidationError("cooldown must include a deadline")
        if self.error_code:
            _code(self.error_code)
        for key, value in self.safe_metadata.items():
            if (
                not _SAFE_CODE.fullmatch(key)
                or _FORBIDDEN_METADATA.search(key)
                or not isinstance(value, bool | int | str)
            ):
                raise ScenarioValidationError("response metadata is unsafe")
        object.__setattr__(self, "safe_metadata", dict(self.safe_metadata))

    def as_job_outcome(self) -> Any:
        """Translate a synthetic response at the generic jobs handler seam."""
        from nfx.jobs.handlers import HandlerOutcome

        result: dict[str, bool | int | str | None] = {
            "outcome": self.outcome.value,
            "unit_count": len(self.units),
            "next_cursor": self.next_cursor,
            "next_nsu": self.next_nsu,
            "coverage": self.coverage.value,
        }
        if self.outcome in {
            FiscalOutcome.SUCCESS,
            FiscalOutcome.EMPTY,
            FiscalOutcome.DUPLICATE,
        }:
            return HandlerOutcome.success(result)
        if self.outcome == FiscalOutcome.COOLDOWN:
            return HandlerOutcome.cooldown(
                cooldown_until=self.cooldown_until,
                error_code=self.error_code or "synthetic_cooldown",
                result=result,
            )
        if self.outcome == FiscalOutcome.BLOCKED:
            return HandlerOutcome.permanent(
                error_code=self.error_code or "synthetic_blocked", result=result
            )
        if self.outcome in {
            FiscalOutcome.UNAVAILABLE,
            FiscalOutcome.TIMEOUT,
            FiscalOutcome.REPEATED_CURSOR,
        }:
            return HandlerOutcome.temporary(
                error_code=self.error_code or self.outcome.value, result=result
            )
        return HandlerOutcome.partial(
            error_code=self.error_code or self.outcome.value, result=result
        )


@dataclass(frozen=True)
class ScenarioStep:
    request_cursor: str | None
    response: FiscalResponse


@dataclass(frozen=True)
class SyntheticScenario:
    name: ScenarioName
    family: FiscalFamily
    seed: int
    steps: tuple[ScenarioStep, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, ScenarioName) or not isinstance(self.family, FiscalFamily):
            raise ScenarioValidationError("scenario identity is invalid")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ScenarioValidationError("scenario seed is invalid")
        if not self.steps:
            raise ScenarioValidationError("scenario must contain an ordered step sequence")
        for step in self.steps:
            if step.request_cursor is not None:
                _reference("request_cursor", step.request_cursor)


@dataclass(frozen=True)
class TransportCall:
    family: FiscalFamily
    source: str
    flow: str
    cursor: str | None
    correlation_id: str


class FakeFiscalTransport:
    """An in-process transport that records requests and performs no I/O."""

    def __init__(self) -> None:
        self.calls: list[TransportCall] = []

    def exchange(
        self, request: FiscalRequest, response: Callable[[], FiscalResponse]
    ) -> FiscalResponse:
        self.calls.append(
            TransportCall(
                family=request.family,
                source=request.source,
                flow=request.flow,
                cursor=request.cursor,
                correlation_id=request.correlation_id,
            )
        )
        return response()


class FiscalAdapter(Protocol):
    family: FiscalFamily

    def collect(self, request: FiscalRequest) -> FiscalResponse: ...


class DeterministicFiscalSimulator:
    """Replays one ordered scenario and never opens a network connection."""

    family: FiscalFamily

    def __init__(
        self, scenario: SyntheticScenario, transport: FakeFiscalTransport | None = None
    ) -> None:
        if scenario.family != self.family:
            raise ScenarioValidationError("scenario family does not match adapter")
        self.scenario = scenario
        self.transport = transport or FakeFiscalTransport()
        self._step_index = 0

    def collect(self, request: FiscalRequest) -> FiscalResponse:
        if request.family != self.family:
            raise ScenarioExecutionError("request family does not match adapter")
        if self._step_index >= len(self.scenario.steps):
            raise ScenarioExecutionError("scenario has no remaining step")
        step = self.scenario.steps[self._step_index]
        if request.cursor != step.request_cursor:
            raise ScenarioExecutionError("request cursor does not match scenario step")
        self._step_index += 1
        response = self.transport.exchange(request, lambda: step.response)
        logger.info(
            "synthetic_fiscal_step",
            extra={
                "scenario": self.scenario.name.value,
                "family": self.family.value,
                "step": self._step_index,
                "outcome": response.outcome.value,
                "correlation_id": request.correlation_id,
            },
        )
        return response


class NFeSimulator(DeterministicFiscalSimulator):
    family = FiscalFamily.NFE


class AdnSimulator(DeterministicFiscalSimulator):
    family = FiscalFamily.ADN


def _unit(
    family: FiscalFamily,
    seed: int,
    label: str,
    *,
    variant: int = 0,
    kind: str = "document",
    parent: str | None = None,
) -> FiscalUnit:
    digest = hashlib.sha256(
        f"nfx-synthetic:{family.value}:{seed}:{label}:{variant}".encode()
    ).hexdigest()
    return FiscalUnit(
        identity=f"synthetic:{family.value}:{seed}:{label}",
        content_hash=digest,
        kind=kind,
        parent_identity=parent,
    )


def _response(
    outcome: FiscalOutcome,
    *,
    units: Sequence[FiscalUnit] = (),
    next_cursor: str | None = None,
    next_nsu: str | None = None,
    coverage: Coverage = Coverage.AVAILABLE,
    error_code: str = "",
    cooldown_until: datetime | None = None,
) -> FiscalResponse:
    return FiscalResponse(
        outcome=outcome,
        units=tuple(units),
        next_cursor=next_cursor,
        next_nsu=next_nsu,
        coverage=coverage,
        error_code=error_code,
        cooldown_until=cooldown_until,
        safe_metadata={"generated": True},
    )


def build_scenario(
    name: ScenarioName | str,
    family: FiscalFamily,
    *,
    seed: int,
) -> SyntheticScenario:
    """Generate a named, replayable fixture without embedding fiscal content."""
    try:
        scenario_name = name if isinstance(name, ScenarioName) else ScenarioName(name)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError("unknown synthetic scenario") from exc
    if not isinstance(family, FiscalFamily):
        raise ScenarioValidationError("unknown synthetic family")
    if not isinstance(seed, int) or seed < 0:
        raise ScenarioValidationError("scenario seed is invalid")

    first = _unit(family, seed, "first")
    second = _unit(family, seed, "second")
    steps: tuple[ScenarioStep, ...]
    if scenario_name == ScenarioName.PAGINATED_SUCCESS:
        continuation = "cursor-1" if family == FiscalFamily.NFE else "nsu-1"
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.SUCCESS,
                    units=(first,),
                    next_cursor=continuation if family == FiscalFamily.NFE else None,
                    next_nsu=continuation if family == FiscalFamily.ADN else None,
                ),
            ),
            ScenarioStep(continuation, _response(FiscalOutcome.SUCCESS, units=(second,))),
        )
    elif scenario_name == ScenarioName.INTERRUPTION_RESTART:
        steps = (
            ScenarioStep(
                None, _response(FiscalOutcome.SUCCESS, units=(first,), next_cursor="cursor-restart")
            ),
            ScenarioStep("cursor-restart", _response(FiscalOutcome.SUCCESS, units=(second,))),
        )
    elif scenario_name == ScenarioName.VALID_EMPTY:
        steps = (ScenarioStep(None, _response(FiscalOutcome.EMPTY)),)
    elif scenario_name == ScenarioName.NO_COVERAGE:
        steps = (ScenarioStep(None, _response(FiscalOutcome.NO_COVERAGE, coverage=Coverage.NONE)),)
    elif scenario_name == ScenarioName.DUPLICATE_EQUAL_HASH:
        steps = (ScenarioStep(None, _response(FiscalOutcome.DUPLICATE, units=(first,))),)
    elif scenario_name == ScenarioName.IDENTITY_CONFLICT:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.CONFLICT,
                    units=(first, _unit(family, seed, "first", variant=1)),
                    error_code="identity_conflict",
                ),
            ),
        )
    elif scenario_name == ScenarioName.TIMEOUT:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.TIMEOUT, coverage=Coverage.UNKNOWN, error_code="source_timeout"
                ),
            ),
        )
    elif scenario_name == ScenarioName.UNAVAILABLE:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.UNAVAILABLE,
                    coverage=Coverage.UNKNOWN,
                    error_code="source_unavailable",
                ),
            ),
        )
    elif scenario_name == ScenarioName.COOLDOWN:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.COOLDOWN,
                    coverage=Coverage.UNKNOWN,
                    error_code="official_cooldown",
                    cooldown_until=datetime(2030, 1, 1, tzinfo=UTC),
                ),
            ),
        )
    elif scenario_name == ScenarioName.PERMANENT_BLOCK:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.BLOCKED,
                    coverage=Coverage.UNKNOWN,
                    error_code="authorization_blocked",
                ),
            ),
        )
    elif scenario_name == ScenarioName.MALFORMED_PAYLOAD:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.MALFORMED,
                    coverage=Coverage.UNKNOWN,
                    error_code="malformed_payload",
                ),
            ),
        )
    elif scenario_name == ScenarioName.EVENT_WITHOUT_PARENT:
        event = _unit(family, seed, "event", kind="event", parent="synthetic:missing-parent")
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.EVENT_WITHOUT_PARENT,
                    units=(event,),
                    error_code="event_parent_missing",
                ),
            ),
        )
    elif scenario_name == ScenarioName.REPEATED_CURSOR:
        steps = (
            ScenarioStep(
                None, _response(FiscalOutcome.SUCCESS, units=(first,), next_cursor="cursor-repeat")
            ),
            ScenarioStep(
                "cursor-repeat",
                _response(
                    FiscalOutcome.REPEATED_CURSOR,
                    next_cursor="cursor-repeat",
                    error_code="cursor_repeated",
                ),
            ),
        )
    else:
        steps = (
            ScenarioStep(
                None,
                _response(
                    FiscalOutcome.PARTIAL,
                    units=(first,),
                    next_cursor="cursor-partial",
                    error_code="partial_result",
                ),
            ),
        )
    return SyntheticScenario(scenario_name, family, seed, steps)


def make_simulator_handler(adapter: FiscalAdapter) -> Callable[[Any], Any]:
    """Build a generic jobs handler from safe job payload references."""

    def handler(job: Any) -> Any:
        payload = job.payload
        try:
            request = FiscalRequest(
                source=payload["source"],
                family=FiscalFamily(payload["family"]),
                actor=payload["actor"],
                flow=payload["flow"],
                cursor=payload.get("cursor"),
                policy_reference=payload["policy_reference"],
                certificate_handle=payload["certificate_handle"],
                correlation_id=payload["correlation_id"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ScenarioExecutionError("synthetic job context is invalid") from exc
        return adapter.collect(request).as_job_outcome()

    return handler
