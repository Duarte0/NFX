from __future__ import annotations

import hashlib
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from django.db import connections
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.audit.models import AuditEvent
from nfx.companies.models import Company, CompanyFlow, FlowFamily
from nfx.documents.models import (
    Document,
    DocumentEvent,
    DocumentEventEvidence,
    DocumentEvidence,
)
from nfx.documents.services import (
    DocumentInput,
    DocumentPersistenceStatus,
    FiscalIdentity,
    persist_document,
)


@pytest.fixture
def company() -> Company:
    company = Company.objects.create(cnpj="11222333000181", legal_name="Empresa Sintética")
    CompanyFlow.objects.create(company=company, family=FlowFamily.NFE)
    return company


def _artifact(*, digest_payload: bytes, logical_key: str) -> Artifact:
    return Artifact.objects.create(
        logical_class="fiscal_original",
        logical_key=logical_key,
        object_key=f"artifacts/{uuid4().hex}/v1",
        digest_algorithm="sha256",
        digest=hashlib.sha256(digest_payload).hexdigest(),
        size_bytes=len(digest_payload),
        declared_mime_type="application/xml",
        detected_mime_type="application/xml",
        state=ArtifactState.FINALIZED,
    )


def _input(
    company: Company, artifact: Artifact, *, identity: str = "synthetic-doc"
) -> DocumentInput:
    return DocumentInput(
        company_id=company.id,
        family="nfe",
        role="entrada",
        category="document",
        source="simulator",
        flow="distribution",
        identity=FiscalIdentity(official_key=identity),
        emitted_at=datetime(2026, 8, 9, 14, 0, tzinfo=UTC),
        authorized_at=datetime(2026, 8, 9, 14, 1, tzinfo=UTC),
        situation="authorized",
        artifact_id=artifact.id,
        origin_execution_ref="execution-synthetic-1",
        correlation_id="corr-synthetic-1",
    )


@pytest.mark.django_db(transaction=True)
def test_document_persistence_replay_and_conflict_preserve_evidence(company: Company) -> None:
    first_artifact = _artifact(digest_payload=b"first", logical_key="first")
    replay_artifact = _artifact(digest_payload=b"first", logical_key="replay")
    conflict_artifact = _artifact(digest_payload=b"different", logical_key="conflict")

    first = persist_document(_input(company, first_artifact))
    replay = persist_document(_input(company, replay_artifact))
    conflict = persist_document(_input(company, conflict_artifact))

    assert first.status == DocumentPersistenceStatus.PERSISTED
    assert replay.status == DocumentPersistenceStatus.REPLAY
    assert conflict.status == DocumentPersistenceStatus.CONFLICT
    assert first.document_id == replay.document_id == conflict.document_id
    assert Document.objects.count() == 1
    assert DocumentEvidence.objects.count() == 2
    assert set(DocumentEvidence.objects.values_list("digest", flat=True)) == {
        hashlib.sha256(b"first").hexdigest(),
        hashlib.sha256(b"different").hexdigest(),
    }
    audit_context = " ".join(
        str(context)
        for context in AuditEvent.objects.filter(entity_type="document").values_list(
            "context", flat=True
        )
    )
    assert hashlib.sha256(b"first").hexdigest() not in audit_context
    assert "first" not in audit_context


@pytest.mark.django_db(transaction=True)
def test_identity_insufficiency_is_quarantined_without_a_falsely_identified_document(
    company: Company,
) -> None:
    artifact = _artifact(digest_payload=b"unknown", logical_key="unknown")
    invalid = _input(company, artifact)
    invalid.identity = FiscalIdentity()

    result = persist_document(invalid)

    assert result.status == DocumentPersistenceStatus.QUARANTINE
    assert result.reason_code == "identity_insufficient"
    assert result.document_id is None
    assert Document.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_event_requires_compatible_parent_and_never_changes_parent_competence(
    company: Company,
) -> None:
    artifact = _artifact(digest_payload=b"parent", logical_key="parent")
    event_artifact = _artifact(digest_payload=b"event", logical_key="event")
    parent = persist_document(_input(company, artifact))
    assert parent.document_id is not None
    event_input = _input(company, event_artifact, identity="synthetic-event")
    event_input.kind = "event"
    event_input.parent_document_id = parent.document_id
    event_input.relationship_type = "substitution"
    event_input.emitted_at = datetime(2027, 1, 1, tzinfo=UTC)
    event_input.authorized_at = None

    event = persist_document(event_input)

    assert event.status == DocumentPersistenceStatus.PERSISTED
    assert event.event_id is not None
    assert DocumentEvent.objects.count() == 1
    assert DocumentEventEvidence.objects.count() == 1
    assert Document.objects.get(pk=parent.document_id).competence.isoformat() == "2026-08-09"


@pytest.mark.django_db(transaction=True)
def test_event_replay_and_conflict_preserve_event_evidence(company: Company) -> None:
    parent_artifact = _artifact(digest_payload=b"parent", logical_key="event-parent")
    first_artifact = _artifact(digest_payload=b"event", logical_key="event-first")
    replay_artifact = _artifact(digest_payload=b"event", logical_key="event-replay")
    conflict_artifact = _artifact(digest_payload=b"changed", logical_key="event-conflict")
    parent = persist_document(_input(company, parent_artifact))

    def event_input(artifact: Artifact) -> DocumentInput:
        data = _input(company, artifact, identity="synthetic-event-replay")
        data.kind = "event"
        data.parent_document_id = parent.document_id
        data.relationship_type = "event"
        data.authorized_at = None
        return data

    first = persist_document(event_input(first_artifact))
    replay = persist_document(event_input(replay_artifact))
    conflict = persist_document(event_input(conflict_artifact))

    assert first.status == DocumentPersistenceStatus.PERSISTED
    assert first.event_id is not None
    assert replay.status == DocumentPersistenceStatus.REPLAY
    assert conflict.status == DocumentPersistenceStatus.CONFLICT
    assert first.event_id == replay.event_id == conflict.event_id
    assert DocumentEvent.objects.count() == 1
    assert DocumentEventEvidence.objects.count() == 2
    assert DocumentEvent.objects.get(pk=first.event_id).state == "conflict"


@pytest.mark.django_db(transaction=True)
def test_event_with_missing_or_incompatible_parent_is_quarantined(company: Company) -> None:
    artifact = _artifact(digest_payload=b"event", logical_key="event-no-parent")
    missing = _input(company, artifact, identity="event-missing")
    missing.kind = "event"
    missing.parent_document_id = uuid4()
    missing.relationship_type = "event"
    missing.authorized_at = None

    result = persist_document(missing)

    assert result.status == DocumentPersistenceStatus.QUARANTINE
    assert result.reason_code == "parent_missing"

    other_company = Company.objects.create(cnpj="22333444000194", legal_name="Outra Sintética")
    other_artifact = _artifact(digest_payload=b"other", logical_key="other-parent")
    other_parent = persist_document(_input(other_company, other_artifact, identity="other-parent"))
    assert other_parent.document_id is not None
    incompatible = _input(company, artifact, identity="event-incompatible")
    incompatible.kind = "event"
    incompatible.parent_document_id = other_parent.document_id
    incompatible.relationship_type = "event"
    incompatible.authorized_at = None

    result = persist_document(incompatible)

    assert result.status == DocumentPersistenceStatus.QUARANTINE
    assert result.reason_code == "parent_incompatible"


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_identity_is_one_document_and_two_replays(
    company: Company,
) -> None:
    artifacts = [
        _artifact(digest_payload=b"same", logical_key=f"race-{index}") for index in range(2)
    ]
    outcomes: list[DocumentPersistenceStatus] = []
    failures: list[BaseException] = []
    barrier = threading.Barrier(2)

    def persist(artifact: Artifact) -> None:
        try:
            connections["default"].close_if_unusable_or_obsolete()
            barrier.wait()
            outcomes.append(persist_document(_input(company, artifact)).status)
        except BaseException as exc:  # pragma: no cover - asserted by caller
            failures.append(exc)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=persist, args=(artifact,)) for artifact in artifacts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not failures
    assert sorted(outcomes) == [
        DocumentPersistenceStatus.PERSISTED,
        DocumentPersistenceStatus.REPLAY,
    ]
    assert Document.objects.count() == 1
