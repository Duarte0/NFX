from __future__ import annotations

import hashlib
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password
from django.test import Client
from django.utils import timezone
from nfx.artifacts.models import Artifact, ArtifactState
from nfx.backup.models import BackupKind, BackupState, RestoreState
from nfx.backup.services import BackupService, RestoreTarget
from nfx.identity.models import IdentitySession, Role, User
from nfx.identity.services import _digest


class MemoryStore:
    def __init__(self, values: dict[str, bytes]) -> None:
        self.values = values

    def read(self, object_key: str) -> BytesIO | None:
        value = self.values.get(object_key)
        return BytesIO(value) if value is not None else None


def _client(role: str) -> Client:
    user = User.objects.create(
        email=f"backup-{role}-{uuid4().hex}@example.test",
        name="Synthetic backup user",
        role=role,
        password_hash=make_password("synthetic-password"),
    )
    token = f"backup-token-{uuid4().hex}"
    IdentitySession.objects.create(
        token_hash=_digest(token),
        user=user,
        revocation_version=user.revocation_version,
        last_activity_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    client = Client()
    client.cookies["nfx_session"] = token
    return client


@pytest.mark.django_db(transaction=True)
def test_backup_manifest_and_isolated_restore_verify_database_and_objects(tmp_path: Path) -> None:
    payload = b"synthetic-original"
    artifact = Artifact.objects.create(
        logical_class="document-original",
        logical_key="document:synthetic:original",
        object_key="artifacts/synthetic-original",
        digest=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        declared_mime_type="application/octet-stream",
        detected_mime_type="application/octet-stream",
        state=ArtifactState.FINALIZED,
    )
    service = BackupService(
        backup_root=tmp_path / "backups",
        object_store=MemoryStore({artifact.object_key: payload}),
        master_key=b"A" * 32,
    )
    backup = service.create_backup(BackupKind.DAILY, database_dump=b"synthetic-db")

    assert backup.state == BackupState.COMPLETE
    assert backup.manifest is not None
    assert backup.manifest_hash
    assert "object_key" not in str(backup.manifest)
    assert backup.manifest["objects"]["count"] == 1

    operation = service.restore(
        backup.id,
        RestoreTarget(root=tmp_path / "isolated", runtime_root=tmp_path / "runtime"),
    )

    assert operation.state == RestoreState.SUCCESS
    assert operation.validations["database"]["hash"] == "verified"
    assert operation.validations["objects"]["hashes"] == "verified"
    assert operation.validations["isolated_target"] is True
    assert (tmp_path / "isolated" / "restore-report.json").exists()


@pytest.mark.django_db(transaction=True)
def test_failed_capture_is_safe_and_idempotent(tmp_path: Path) -> None:
    service = BackupService(backup_root=tmp_path / "backups", object_store=MemoryStore({}))

    first = service.create_backup(
        BackupKind.DAILY, idempotency_key="backup:synthetic:1", database_dump=b"db"
    )
    second = service.create_backup(
        BackupKind.DAILY, idempotency_key="backup:synthetic:1", database_dump=b"different"
    )

    assert first.id == second.id
    assert first.state == BackupState.COMPLETE


@pytest.mark.django_db(transaction=True)
def test_restore_rejects_live_target_without_writing_it(tmp_path: Path) -> None:
    service = BackupService(backup_root=tmp_path / "backups", object_store=MemoryStore({}))
    backup = service.create_backup(BackupKind.DAILY, database_dump=b"db")
    runtime = tmp_path / "runtime"

    operation = service.restore(backup.id, RestoreTarget(root=runtime, runtime_root=runtime))

    assert operation.state == RestoreState.FAILED
    assert operation.safe_error == "live_target"
    assert not runtime.exists()


@pytest.mark.django_db(transaction=True)
def test_backup_status_is_administrator_only_without_existence_leak() -> None:
    assert Client().get("/api/backups/status").status_code == 403
    assert _client(Role.VIEWER).get("/api/backups/status").status_code == 403

    response = _client(Role.ADMINISTRATOR).get("/api/backups/status")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert "backup_path" not in response.content.decode()
