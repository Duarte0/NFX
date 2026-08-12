from __future__ import annotations

import threading
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import make_password
from django.db import connections
from nfx.artifacts.models import ArtifactState
from nfx.artifacts.storage import ArtifactError, ArtifactStorageService, ObjectMetadata
from nfx.backup.models import BackupKind, BackupState
from nfx.backup.services import BackupError, BackupService
from nfx.companies.models import Company, CompanyFlow, CompanyStatus, FlowFamily, FlowState
from nfx.identity.models import Role, User
from nfx.jobs.handlers import HandlerOutcome, clear_handlers, register_handler
from nfx.jobs.models import Job, JobState
from nfx.jobs.services import JobEngine, process_one


class FailingObjectStore:
    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        raise OSError("synthetic object-store outage")

    def head(self, object_key: str) -> None:
        return None

    def read(self, object_key: str) -> None:
        return None

    def list_keys(self, prefix: str) -> Iterator[str]:
        yield from ()

    def delete(self, object_key: str) -> None:
        return None


@pytest.fixture(autouse=True)
def clear_synthetic_handlers() -> None:
    clear_handlers()
    yield
    clear_handlers()


@pytest.mark.django_db(transaction=True)
def test_synthetic_capacity_exercise_uses_bounded_concurrency_without_logical_duplicates() -> None:
    """Exercise the durable company/flow/job path with only synthetic references."""

    company_count = 200
    user_count = 3
    flow_families = (FlowFamily.NFE, FlowFamily.NFSE)
    worker_count = 4
    companies = [
        Company(
            cnpj=f"synthetic-company-{index:04d}",
            legal_name=f"Synthetic Company {index:04d}",
            status=CompanyStatus.ACTIVE,
        )
        for index in range(1, company_count + 1)
    ]
    Company.objects.bulk_create(companies)
    users = [
        User(
            email=f"synthetic-user-{index}@example.test",
            name=f"Synthetic User {index}",
            role=role,
            password_hash=make_password("synthetic-password"),
        )
        for index, role in enumerate(
            (Role.ADMINISTRATOR, Role.OPERATOR, Role.VIEWER), start=1
        )
    ]
    User.objects.bulk_create(users)
    CompanyFlow.objects.bulk_create(
        [
            CompanyFlow(company=company, family=family, state=FlowState.ENABLED)
            for company in companies
            for family in flow_families
        ]
    )

    effects: set[str] = set()
    duplicate_targets: set[str] = set()
    effects_lock = threading.Lock()

    def synthetic_handler(job: Job) -> HandlerOutcome:
        target = job.logical_target
        with effects_lock:
            if target in effects:
                duplicate_targets.add(target)
            effects.add(target)
        return HandlerOutcome.success({"reference_id": f"effect:{job.id}"})

    register_handler("hardening.synthetic", synthetic_handler)
    engine = JobEngine()
    expected_jobs = company_count * len(flow_families)
    for company in companies:
        for family in flow_families:
            target = f"company:{company.id}:flow:{family}"
            engine.enqueue(
                job_type="hardening.synthetic",
                logical_target=target,
                payload={"company_id": str(company.id), "flow": family},
                idempotency_key=f"hardening:{company.id}:{family}",
            )

    started = perf_counter()

    def drain(owner_number: int) -> int:
        processed = 0
        try:
            while process_one(engine, owner=f"hardening-worker-{owner_number}"):
                processed += 1
            return processed
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        processed = sum(pool.map(drain, range(worker_count)))
    elapsed_ms = round((perf_counter() - started) * 1000)

    assert Company.objects.count() == company_count
    assert User.objects.count() == user_count
    assert CompanyFlow.objects.count() == expected_jobs
    assert Job.objects.filter(state=JobState.COMPLETED).count() == expected_jobs
    assert processed == expected_jobs
    assert len(effects) == expected_jobs
    assert not duplicate_targets

    print(
        "P9_CAPACITY_EVIDENCE "
        f"companies={company_count} users={user_count} flows={expected_jobs} "
        f"jobs={expected_jobs} workers={worker_count} elapsed_ms={elapsed_ms} "
        "company_limit=none user_limit=none threshold_classification=proposed"
    )


@pytest.mark.django_db(transaction=True)
def test_storage_outage_and_disk_full_keep_recovery_state_and_safe_backup_status(
    tmp_path: Path,
) -> None:
    artifact_service = ArtifactStorageService(FailingObjectStore(), maximum_size=32)
    artifact = artifact_service.begin(
        "fiscal_original", "document:synthetic:outage", "application/octet-stream"
    )

    with pytest.raises(ArtifactError, match="Object storage write failed"):
        artifact_service.transmit(artifact.id, [b"synthetic-original"])
    artifact.refresh_from_db()
    assert artifact.state == ArtifactState.PENDING
    assert artifact.finalized_at is None

    backup_service = BackupService(
        backup_root=tmp_path / "backups",
        object_store=FailingObjectStore(),
        master_key=b"A" * 32,
    )
    with patch("nfx.backup.services._write_bytes", side_effect=BackupError("insufficient_space")):
        backup = backup_service.create_backup(BackupKind.DAILY, database_dump=b"synthetic-db")

    assert backup.state == BackupState.FAILED
    assert backup.safe_error == "insufficient_space"
    assert backup.backup_path == ""
    assert not list((tmp_path / "backups").glob("*.partial"))
    status = backup_service.status()
    assert status["status"] == "failure"
    assert status["latest_backup"]["safe_error"] == "insufficient_space"
    assert "synthetic-db" not in str(status)
