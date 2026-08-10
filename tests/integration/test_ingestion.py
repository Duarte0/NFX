from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime

import pytest
from nfx.adapters.nfe import (
    NFeDistributionRequest,
    NFeDistributionSimulator,
    NFeFlow,
    NFePosition,
)
from nfx.adapters.simulation import (
    FiscalFamily,
    FiscalOutcome,
    FiscalResponse,
    FiscalUnit,
    ScenarioName,
    build_scenario,
)
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.collection.ingestion import (
    IngestionContext,
    IngestionDocumentMetadata,
    IngestionPageState,
    UnitOutcome,
    ingest_page,
    reconcile_ingestion,
)
from nfx.collection.models import (
    IngestionCheckpoint,
    IngestionOutcome,
    IngestionPage,
    IngestionRecovery,
    ReceivedUnit,
    ReceivedUnitState,
)
from nfx.companies.models import Company
from nfx.documents.models import Document, DocumentEvidence
from nfx.documents.services import FiscalIdentity


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_writes = False

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        if self.fail_writes:
            raise RuntimeError("synthetic object outage")
        payload = b"".join(chunks)
        if len(payload) > maximum_size:
            raise RuntimeError("synthetic object too large")
        self.objects[object_key] = (payload, content_type)
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def head(self, object_key: str) -> ObjectMetadata | None:
        item = self.objects.get(object_key)
        if item is None:
            return None
        payload, content_type = item
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def read(self, object_key: str) -> io.BytesIO | None:
        item = self.objects.get(object_key)
        return None if item is None else io.BytesIO(item[0])

    def list_keys(self, prefix: str) -> Iterator[str]:
        yield from (key for key in self.objects if key.startswith(prefix))


@pytest.fixture
def company() -> Company:
    return Company.objects.create(cnpj="11222333000182", legal_name="Ingestão Sintética")


@pytest.fixture
def storage() -> tuple[ArtifactStorageService, MemoryObjectStore]:
    store = MemoryObjectStore()
    return ArtifactStorageService(store), store


def _context(company: Company, *, cursor: str | None = None) -> IngestionContext:
    return IngestionContext(
        company_id=company.id,
        family="nfe",
        flow="received",
        execution_ref="execution:synthetic-1",
        correlation_id="correlation:synthetic-1",
        request_cursor=cursor,
    )


def _unit(identity: str = "synthetic:unit-1", payload: bytes | None = None) -> FiscalUnit:
    payload = payload or f"nfx-synthetic-unit:{identity}".encode()
    return FiscalUnit(identity=identity, content_hash=hashlib.sha256(payload).hexdigest())


def _metadata(unit: FiscalUnit, _: IngestionContext) -> IngestionDocumentMetadata:
    return IngestionDocumentMetadata(
        emitted_at=datetime(2026, 8, 9, 14, 0, tzinfo=UTC),
        identity=FiscalIdentity(external_id=unit.identity),
    )


@pytest.mark.django_db(transaction=True)
def test_page_is_durable_before_cursor_progress_and_replay_is_idempotent(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, _ = storage
    first = _unit()
    payloads = {
        first.content_hash: f"nfx-synthetic-unit:{first.identity}".encode(),
        hashlib.sha256(b"changed").hexdigest(): b"changed",
    }
    response = FiscalResponse(FiscalOutcome.SUCCESS, units=(first,), next_cursor="cursor:1")
    result = ingest_page(
        artifact_service,
        _context(company),
        response,
        payload_factory=lambda unit: (payloads[unit.content_hash],),
        metadata_factory=_metadata,
    )

    assert result.page_state == IngestionPageState.COMPLETE
    assert result.advanced is True
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"
    assert Document.objects.count() == 1
    assert ReceivedUnit.objects.get().state == ReceivedUnitState.PERSISTED

    replay = ingest_page(
        artifact_service,
        _context(company),
        response,
        payload_factory=lambda unit: (payloads[unit.content_hash],),
        metadata_factory=_metadata,
    )
    assert replay.page_id == result.page_id
    assert replay.unit_states == (UnitOutcome.PERSISTED,)
    assert Document.objects.count() == 1
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"


@pytest.mark.django_db(transaction=True)
def test_object_failure_leaves_retryable_unit_and_reconciliation_advances(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, store = storage
    unit = _unit()
    store.fail_writes = True
    failed = ingest_page(
        artifact_service,
        _context(company),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(unit,), next_cursor="cursor:1"),
        metadata_factory=_metadata,
    )
    assert failed.page_state == IngestionPageState.PARTIAL
    assert failed.advanced is False
    assert ReceivedUnit.objects.get().state == ReceivedUnitState.FAILED
    assert not IngestionCheckpoint.objects.get(company=company, family="nfe").cursor

    store.fail_writes = False
    assert reconcile_ingestion(artifact_service) == 1
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"
    assert ReceivedUnit.objects.get().state == ReceivedUnitState.PERSISTED


@pytest.mark.django_db(transaction=True)
def test_quarantine_is_terminal_but_stale_and_repeated_positions_do_not_advance(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, _ = storage
    unit = _unit(identity="synthetic:quarantine")
    quarantined = ingest_page(
        artifact_service,
        _context(company),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(unit,), next_cursor="cursor:1"),
        metadata_factory=lambda _unit, _context: IngestionDocumentMetadata(
            emitted_at=datetime(2026, 8, 9, 14, 0, tzinfo=UTC), identity=FiscalIdentity()
        ),
    )
    assert quarantined.unit_states == (UnitOutcome.QUARANTINE,)
    assert quarantined.advanced is True

    stale = ingest_page(
        artifact_service,
        IngestionContext(
            company_id=company.id,
            family="nfe",
            flow="received",
            execution_ref="execution:synthetic-1",
            correlation_id="correlation:synthetic-1",
            request_cursor="cursor:old",
        ),
        FiscalResponse(FiscalOutcome.EMPTY, next_cursor="cursor:new"),
    )
    assert stale.page_state == IngestionPageState.FAILED
    assert stale.safe_reason == "stale_cursor"
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("outcome", "expected_state", "expected_outcome", "expected_recovery"),
    [
        (
            FiscalOutcome.NO_COVERAGE,
            IngestionPageState.NO_COVERAGE,
            IngestionOutcome.NO_COVERAGE,
            IngestionRecovery.NONE,
        ),
        (
            FiscalOutcome.UNAVAILABLE,
            IngestionPageState.UNAVAILABLE,
            IngestionOutcome.UNAVAILABLE,
            IngestionRecovery.RETRY,
        ),
        (
            FiscalOutcome.TIMEOUT,
            IngestionPageState.RETRY,
            IngestionOutcome.TEMPORARY_FAILURE,
            IngestionRecovery.RETRY,
        ),
        (
            FiscalOutcome.COOLDOWN,
            IngestionPageState.COOLDOWN,
            IngestionOutcome.COOLDOWN,
            IngestionRecovery.COOLDOWN,
        ),
        (
            FiscalOutcome.BLOCKED,
            IngestionPageState.BLOCKED,
            IngestionOutcome.PERMANENT_FAILURE,
            IngestionRecovery.BLOCKED,
        ),
        (
            FiscalOutcome.CONFLICT,
            IngestionPageState.FAILED,
            IngestionOutcome.CONFLICT,
            IngestionRecovery.CONFLICT_REVIEW,
        ),
        (
            FiscalOutcome.MALFORMED,
            IngestionPageState.FAILED,
            IngestionOutcome.MALFORMED,
            IngestionRecovery.QUARANTINE,
        ),
        (
            FiscalOutcome.REPEATED_CURSOR,
            IngestionPageState.RETRY,
            IngestionOutcome.TEMPORARY_FAILURE,
            IngestionRecovery.RECONCILE,
        ),
    ],
)
def test_response_failure_matrix_is_durable_and_does_not_advance(
    company: Company,
    storage: tuple[ArtifactStorageService, MemoryObjectStore],
    outcome: FiscalOutcome,
    expected_state: IngestionPageState,
    expected_outcome: IngestionOutcome,
    expected_recovery: IngestionRecovery,
) -> None:
    artifact_service, _ = storage
    response = FiscalResponse(
        outcome,
        next_cursor="cursor:unsafe",
        cooldown_until=(
            datetime(2026, 8, 10, tzinfo=UTC) if outcome == FiscalOutcome.COOLDOWN else None
        ),
        error_code="source_unavailable" if outcome == FiscalOutcome.UNAVAILABLE else "",
    )

    result = ingest_page(artifact_service, _context(company), response)
    page = IngestionPage.objects.get(id=result.page_id)

    assert result.page_state == expected_state
    assert result.outcome == expected_outcome
    assert result.recovery == expected_recovery
    assert page.outcome == expected_outcome
    assert page.recovery == expected_recovery
    assert result.advanced is False
    assert not IngestionCheckpoint.objects.get(company=company, family="nfe").cursor


@pytest.mark.django_db(transaction=True)
def test_unavailable_page_can_retry_with_same_position_and_then_advance(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, _ = storage
    unavailable = ingest_page(
        artifact_service,
        _context(company),
        FiscalResponse(FiscalOutcome.UNAVAILABLE, next_cursor="cursor:ignored"),
    )
    assert unavailable.outcome == IngestionOutcome.UNAVAILABLE

    unit = _unit(identity="synthetic:after-retry")
    recovered = ingest_page(
        artifact_service,
        _context(company),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(unit,), next_cursor="cursor:1"),
        metadata_factory=_metadata,
    )

    assert recovered.page_id == unavailable.page_id
    assert recovered.page_state == IngestionPageState.COMPLETE
    assert recovered.advanced is True
    assert recovered.outcome == IngestionOutcome.SUCCESS
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"

    repeated = ingest_page(
        artifact_service,
        _context(company, cursor="cursor:1"),
        FiscalResponse(FiscalOutcome.EMPTY, next_cursor="cursor:1"),
    )
    assert repeated.page_state == IngestionPageState.FAILED
    assert repeated.safe_reason == "repeated_cursor"
    assert repeated.outcome == IngestionOutcome.TEMPORARY_FAILURE
    assert repeated.recovery == IngestionRecovery.RECONCILE
    assert IngestionCheckpoint.objects.get(company=company, family="nfe").cursor == "cursor:1"


@pytest.mark.django_db(transaction=True)
def test_divergent_hash_preserves_both_artifacts_and_adn_uses_an_independent_nsu(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, _ = storage
    first = _unit(identity="synthetic:conflict", payload=b"first")
    second = _unit(identity="synthetic:conflict", payload=b"changed")
    payloads = {first.content_hash: b"first", second.content_hash: b"changed"}

    ingest_page(
        artifact_service,
        _context(company),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(first,), next_cursor="cursor:1"),
        payload_factory=lambda unit: (payloads[unit.content_hash],),
        metadata_factory=_metadata,
    )
    conflict = ingest_page(
        artifact_service,
        _context(company, cursor="cursor:1"),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(second,)),
        payload_factory=lambda unit: (payloads[unit.content_hash],),
        metadata_factory=_metadata,
    )

    assert conflict.unit_states == (UnitOutcome.CONFLICT,)
    assert Document.objects.count() == 1
    assert DocumentEvidence.objects.count() == 2

    adn = ingest_page(
        artifact_service,
        IngestionContext(
            company_id=company.id,
            family="adn",
            flow="received",
            execution_ref="execution:adn-1",
            correlation_id="correlation:adn-1",
        ),
        FiscalResponse(FiscalOutcome.EMPTY, next_nsu="nsu:1"),
    )
    assert adn.advanced is True
    assert IngestionCheckpoint.objects.get(company=company, family="adn").nsu == "nsu:1"
    assert not IngestionCheckpoint.objects.get(company=company, family="adn").cursor


@pytest.mark.django_db(transaction=True)
def test_nfe_distribution_handoff_owns_independent_flow_checkpoints(
    company: Company, storage: tuple[ArtifactStorageService, MemoryObjectStore]
) -> None:
    artifact_service, _ = storage
    simulator = NFeDistributionSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.NFE, seed=211)
    )

    def distribution_request(
        flow: NFeFlow,
        position: NFePosition | None = None,
        *,
        company_id: object = company.id,
    ) -> NFeDistributionRequest:
        return NFeDistributionRequest(
            company_id=company_id,
            flow=flow,
            source="synthetic",
            actor="actor:synthetic-001",
            position=position,
            policy_reference="policy:synthetic-v1",
            certificate_handle="certificate:synthetic-001",
            correlation_id=f"correlation:nfe-{flow.value}",
            execution_ref=f"execution:nfe-{flow.value}",
        )

    received = simulator.ingest(
        artifact_service,
        distribution_request(NFeFlow.RECEIVED),
        metadata_factory=_metadata,
    )
    issued = simulator.ingest(
        artifact_service,
        distribution_request(NFeFlow.ISSUED),
        metadata_factory=_metadata,
    )

    assert received.advanced is True
    assert issued.advanced is True
    assert IngestionCheckpoint.objects.get(
        company=company, family="nfe", flow="received"
    ).cursor == "cursor-1"
    assert IngestionCheckpoint.objects.get(
        company=company, family="nfe", flow="issued"
    ).cursor == "cursor-1"
    assert IngestionPage.objects.filter(company=company, family="nfe").count() == 2
    assert ReceivedUnit.objects.filter(company=company, family="nfe").count() == 2

    unavailable = NFeDistributionSimulator(
        build_scenario(ScenarioName.UNAVAILABLE, FiscalFamily.NFE, seed=213)
    )
    failed_company = Company.objects.create(cnpj="22333444000181", legal_name="Falha Sintética")
    failed = unavailable.ingest(
        artifact_service,
        distribution_request(NFeFlow.RECEIVED, company_id=failed_company.id),
    )

    assert failed.advanced is False
    assert IngestionCheckpoint.objects.get(
        company=failed_company, family="nfe", flow="received"
    ).cursor == ""
