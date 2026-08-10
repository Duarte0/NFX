from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable, Iterator
from dataclasses import replace
from uuid import uuid4

import pytest
from nfx.adapters.adn import AdnDistributionRequest, AdnDistributionSimulator, AdnFlow, AdnPosition
from nfx.adapters.simulation import FiscalFamily, FiscalOutcome, ScenarioName, build_scenario
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.collection.models import IngestionCheckpoint, IngestionPage, ReceivedUnit
from nfx.companies.models import AdnCoverageSnapshot, Company
from nfx.documents.models import Document, DocumentEvent


class MemoryObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
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
    return Company.objects.create(cnpj="11222333000182", legal_name="ADN Sintético")


@pytest.fixture
def storage() -> ArtifactStorageService:
    return ArtifactStorageService(MemoryObjectStore())


def _request(company: Company, *, flow: AdnFlow = AdnFlow.PROVIDED) -> AdnDistributionRequest:
    return AdnDistributionRequest(
        company_id=company.id,
        actor="actor:synthetic-001",
        flow=flow,
        source="synthetic",
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id=f"correlation:{uuid4()}",
        execution_ref="execution:adn-synthetic",
    )


@pytest.mark.django_db(transaction=True)
def test_adn_handoff_preserves_originals_links_events_and_scoped_nsu(
    company: Company, storage: ArtifactStorageService
) -> None:
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.SUBSTITUTION, FiscalFamily.ADN, seed=503)
    )
    result = simulator.ingest(storage, _request(company))

    assert result.advanced is False
    assert result.outcome.value == "success"
    assert IngestionCheckpoint.objects.get(
        company=company, family="adn", flow="actor:synthetic-001:provided"
    ).nsu == ""
    assert IngestionPage.objects.get(company=company, family="adn").state == "complete"
    assert ReceivedUnit.objects.filter(company=company, family="adn").count() == 2
    assert (
        DocumentEvent.objects.filter(
            parent_document__company=company, relationship_type="substitution"
        ).count()
        == 1
    )
    assert Document.objects.get(company=company).role == "prestada"
    snapshot = AdnCoverageSnapshot.objects.get(company=company)
    assert snapshot.status == "available"
    assert snapshot.evidence_reference == "coverage:actor:synthetic-001:provided"


@pytest.mark.django_db(transaction=True)
def test_no_coverage_is_persisted_and_does_not_advance_nsu(
    company: Company, storage: ArtifactStorageService
) -> None:
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.NO_COVERAGE, FiscalFamily.ADN, seed=509)
    )
    result = simulator.ingest(storage, _request(company))

    assert result.outcome == "no_coverage"
    assert result.advanced is False
    assert IngestionCheckpoint.objects.get(
        company=company, family="adn", flow="actor:synthetic-001:provided"
    ).nsu == ""
    assert AdnCoverageSnapshot.objects.get(company=company).status == "none"


@pytest.mark.django_db(transaction=True)
def test_actor_and_flow_checkpoints_are_independent(
    company: Company, storage: ArtifactStorageService
) -> None:
    simulator = AdnDistributionSimulator(
        build_scenario(ScenarioName.PAGINATED_SUCCESS, FiscalFamily.ADN, seed=511)
    )
    first = simulator.ingest(storage, _request(company, flow=AdnFlow.TAKEN))
    second = simulator.ingest(storage, _request(company, flow=AdnFlow.PROVIDED))

    assert first.advanced is True and second.advanced is True
    assert IngestionCheckpoint.objects.filter(company=company, family="adn").count() == 2
    assert IngestionCheckpoint.objects.get(
        company=company, family="adn", flow="actor:synthetic-001:taken"
    ).nsu == "nsu-1"
    assert IngestionCheckpoint.objects.get(
        company=company, family="adn", flow="actor:synthetic-001:provided"
    ).nsu == "nsu-1"

    replay = simulator.distribute(
        replace(
            _request(company),
            position=AdnPosition("actor:synthetic-001", AdnFlow.PROVIDED, "nsu-1"),
        )
    )
    assert replay.outcome == FiscalOutcome.SUCCESS
