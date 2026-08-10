from __future__ import annotations

import hashlib
import io
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from nfx.adapters.nfe import (
    NFeEventRequest,
    NFeFlow,
    NFeFollowUpAdapter,
    NFeFollowUpScenarioName,
    NFeFollowUpService,
    NFeFollowUpSimulator,
    NFeManifestationAdapter,
    NFeManifestationRequest,
    NFeManifestationScenarioName,
    NFeManifestationSimulator,
    NFeManifestationType,
    NFeScienceRequest,
    build_nfe_followup_scenario,
    build_nfe_manifestation_scenario,
    ensure_nfe_followup_handler,
)
from nfx.adapters.simulation import FiscalOutcome, FiscalResponse
from nfx.artifacts.storage import ArtifactStorageService, ObjectMetadata
from nfx.certificates.models import Certificate, CertificateState
from nfx.collection.ingestion import IngestionContext, ingest_page, reconcile_ingestion
from nfx.collection.models import ReceivedUnit, ReceivedUnitState
from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowFamily
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEvidence,
    NFeManifestation,
)
from nfx.documents.services import DocumentInput, FiscalIdentity, persist_document
from nfx.identity.models import Role, User
from nfx.identity.services import SessionIdentity
from nfx.jobs.handlers import clear_handlers
from nfx.jobs.models import Job, JobState
from nfx.jobs.policy import create_policy
from nfx.jobs.services import JobEngine, process_one

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


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
        value = self.objects.get(object_key)
        if value is None:
            return None
        payload, content_type = value
        return ObjectMetadata(len(payload), hashlib.sha256(payload).hexdigest(), content_type)

    def read(self, object_key: str) -> io.BytesIO | None:
        value = self.objects.get(object_key)
        return io.BytesIO(value[0]) if value else None

    def list_keys(self, prefix: str) -> Iterator[str]:
        yield from (key for key in self.objects if key.startswith(prefix))


@pytest.fixture(autouse=True)
def reset_handlers() -> Iterator[None]:
    clear_handlers()
    yield
    clear_handlers()


@pytest.fixture
def company() -> Company:
    company = Company.objects.create(
        cnpj=f"11222333000{Company.objects.count() + 181:03d}",
        legal_name="NF-e Follow-up Synthetic",
        status=CompanyStatus.ACTIVE,
    )
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    Certificate.objects.create(
        company=company,
        encrypted_data_key=b"synthetic-key",
        data_key_nonce=b"synthetic-nonce",
        encrypted_password=b"synthetic-password",
        password_nonce=b"synthetic-password-nonce",
        fingerprint_sha256=("a" * 63) + str(Company.objects.count() % 10),
        certificate_cnpj=company.cnpj,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=365),
        state=CertificateState.CURRENT,
        activated_at=NOW,
    )
    return company


@pytest.fixture
def storage() -> ArtifactStorageService:
    return ArtifactStorageService(MemoryObjectStore())


def _parent(company: Company, storage: ArtifactStorageService, identity: str) -> Document:
    payload = f"parent:{identity}".encode()
    artifact = storage.begin("fiscal_original", f"parent:{identity}", "application/octet-stream")
    storage.transmit(artifact.id, (payload,))
    result = persist_document(
        DocumentInput(
            company_id=company.id,
            family="nfe",
            role="entrada",
            category="document",
            source="synthetic",
            flow="received",
            identity=FiscalIdentity(external_id=identity),
            emitted_at=NOW,
            authorized_at=NOW,
            artifact_id=artifact.id,
            origin_execution_ref="execution:parent",
            correlation_id="correlation:parent",
        )
    )
    assert result.document_id is not None
    return Document.objects.get(id=result.document_id)


def _request(company: Company, document: Document, correlation: str) -> NFeScienceRequest:
    return NFeScienceRequest(
        company_id=company.id,
        document_id=document.id,
        flow=NFeFlow.RECEIVED,
        source="synthetic",
        actor="actor:synthetic-001",
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id=correlation,
    )


def _manifestation_request(
    company: Company, document_id: object, correlation: str, idempotency: str
) -> NFeManifestationRequest:
    return NFeManifestationRequest(
        company_id=company.id,
        document_id=document_id,
        flow=NFeFlow.RECEIVED,
        manifestation_type=NFeManifestationType.SCIENCE_OF_OPERATION,
        source="synthetic",
        actor="actor:synthetic-001",
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id=correlation,
        idempotency_reference=idempotency,
    )


@pytest.mark.django_db(transaction=True)
def test_permitted_science_enqueues_xml_and_persists_original_before_xml(
    company: Company, storage: ArtifactStorageService
) -> None:
    parent = _parent(company, storage, "synthetic:nfe:619:first")
    actor_user = User.objects.create(
        email="nfe-followup@example.test",
        name="Synthetic operator",
        role=Role.OPERATOR,
        password_hash=make_password("synthetic-password"),
    )
    actor = SessionIdentity(str(actor_user.id), actor_user.email, actor_user.name, actor_user.role)
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="nfe",
        version=1,
        valid_from=NOW - timedelta(days=1),
        retry_limit=2,
    )
    service = NFeFollowUpService(
        NFeFollowUpAdapter(
            NFeFollowUpSimulator(
                build_nfe_followup_scenario(NFeFollowUpScenarioName.PERMITTED, seed=619)
            )
        ),
        storage,
    )
    request = _request(company, parent, "correlation:science-619")

    first = service.enqueue_science(request, actor, policy=policy)
    replay = service.enqueue_science(request, actor, policy=policy)
    assert first.id == replay.id

    ensure_nfe_followup_handler(service)
    engine = JobEngine()
    assert process_one(engine, owner="worker-nfe-followup") is True
    assert Job.objects.get(id=first.id).state == JobState.COMPLETED
    xml_job = Job.objects.get(job_type="nfe.complete_xml")
    assert process_one(engine, owner="worker-nfe-followup") is True
    assert xml_job.refresh_from_db() is None
    assert xml_job.state == JobState.COMPLETED
    evidence = list(DocumentEvidence.objects.filter(document=parent).select_related("artifact"))
    assert {row.artifact.logical_class for row in evidence} == {"fiscal_original", "fiscal_xml"}
    assert DocumentEvidence.objects.filter(document=parent).count() == 3


@pytest.mark.django_db(transaction=True)
def test_event_is_linked_and_event_before_parent_is_replayed_safely(
    company: Company, storage: ArtifactStorageService
) -> None:
    parent = _parent(company, storage, "synthetic:nfe:631:first")
    service = NFeFollowUpService(
        NFeFollowUpAdapter(
            NFeFollowUpSimulator(
                build_nfe_followup_scenario(NFeFollowUpScenarioName.EVENT_WITH_PARENT, seed=631)
            )
        ),
        storage,
    )
    event_request = NFeEventRequest(
        company_id=company.id,
        parent_document_id=parent.id,
        flow=NFeFlow.RECEIVED,
        source="synthetic",
        actor="actor:synthetic-001",
        policy_reference="policy:synthetic-v1",
        certificate_handle="certificate:synthetic-001",
        correlation_id="correlation:event-631",
    )

    result = service.ingest_events(storage, event_request)
    assert result.page_state.value == "complete"
    assert DocumentEvent.objects.filter(parent_document=parent).count() == 1
    assert (
        ReceivedUnit.objects.filter(flow="received:followup").get().state
        == ReceivedUnitState.PERSISTED
    )

    missing = build_nfe_followup_scenario(NFeFollowUpScenarioName.EVENT_WITHOUT_PARENT, seed=641)
    missing_unit = missing.event_response.units[0]
    page = ingest_page(
        storage,
        IngestionContext(
            company_id=company.id,
            family="nfe",
            flow="received:followup",
            document_flow="received",
            page_key="followup:correlation:event-641",
            source="synthetic",
            execution_ref="execution:correlation:event-641",
            correlation_id="correlation:event-641",
        ),
        FiscalResponse(FiscalOutcome.SUCCESS, units=(missing_unit,)),
    )
    assert page.unit_states == ("quarantine",)
    assert (
        ReceivedUnit.objects.get(identity=missing_unit.identity).state
        == ReceivedUnitState.QUARANTINE
    )
    _parent(company, storage, missing_unit.parent_identity or "")
    assert reconcile_ingestion(storage) == 1
    assert DocumentEvent.objects.filter(parent_document__company=company).count() == 2


@pytest.mark.django_db(transaction=True)
def test_manifestation_is_idempotent_and_links_one_nf_e(
    company: Company, storage: ArtifactStorageService
) -> None:
    parent = _parent(company, storage, "synthetic:nfe:651:first")
    actor_user = User.objects.create(
        email="manifestation@example.test",
        name="Synthetic operator",
        role=Role.OPERATOR,
        password_hash=make_password("synthetic-password"),
    )
    actor = SessionIdentity(str(actor_user.id), actor_user.email, actor_user.name, actor_user.role)
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="nfe",
        version=1,
        valid_from=NOW - timedelta(days=1),
        retry_limit=2,
    )
    simulator = NFeManifestationSimulator(
        build_nfe_manifestation_scenario(NFeManifestationScenarioName.ACCEPTED)
    )
    service = NFeFollowUpService(
        NFeFollowUpAdapter(
            NFeFollowUpSimulator(
                build_nfe_followup_scenario(NFeFollowUpScenarioName.DENIED, seed=653)
            )
        ),
        storage,
        manifestation_adapter=NFeManifestationAdapter(simulator),
    )
    request = _manifestation_request(
        company, parent.id, "correlation:manifestation-651", "idempotency:manifestation-651"
    )

    first = service.enqueue_manifestation(request, actor, policy=policy)
    replay = service.enqueue_manifestation(request, actor, policy=policy)
    assert first.id == replay.id

    ensure_nfe_followup_handler(service)
    assert process_one(JobEngine(), owner="worker-manifestation") is True
    manifestation = NFeManifestation.objects.get(id=first.payload["manifestation_id"])
    assert manifestation.state == "accepted"
    assert manifestation.document_id == parent.id
    assert manifestation.safe_result["manifestation_id"] == str(manifestation.id)
    assert simulator.calls() == ("manifestation",)
    assert NFeManifestation.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_manifestation_missing_parent_is_quarantined_without_transport_call(
    company: Company, storage: ArtifactStorageService
) -> None:
    missing_id = uuid4()
    actor_user = User.objects.create(
        email="manifestation-missing@example.test",
        name="Synthetic operator",
        role=Role.OPERATOR,
        password_hash=make_password("synthetic-password"),
    )
    actor = SessionIdentity(str(actor_user.id), actor_user.email, actor_user.name, actor_user.role)
    policy = create_policy(
        source_scope="synthetic",
        flow_scope="nfe",
        version=1,
        valid_from=NOW - timedelta(days=1),
        retry_limit=2,
    )
    simulator = NFeManifestationSimulator()
    service = NFeFollowUpService(
        NFeFollowUpAdapter(
            NFeFollowUpSimulator(
                build_nfe_followup_scenario(NFeFollowUpScenarioName.DENIED, seed=659)
            )
        ),
        storage,
        manifestation_adapter=NFeManifestationAdapter(simulator),
    )
    job = service.enqueue_manifestation(
        _manifestation_request(
            company,
            missing_id,
            "correlation:manifestation-659",
            "idempotency:manifestation-659",
        ),
        actor,
        policy=policy,
    )

    ensure_nfe_followup_handler(service)
    assert process_one(JobEngine(), owner="worker-manifestation") is True
    manifestation = NFeManifestation.objects.get(id=job.payload["manifestation_id"])
    assert manifestation.state == "quarantined"
    assert manifestation.result_code == "parent_missing"
    assert manifestation.document_id is None
    assert simulator.calls() == ()
