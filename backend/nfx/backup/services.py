"""Safe backup capture, verification, retention, and isolated restore.

The archive format is intentionally local and boring: a serialized database
snapshot, verified artifact bytes, encrypted certificate probes, and a
manifest hash. The manifest contains identifiers and digests only.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from django.apps import apps
from django.core import serializers
from django.utils import timezone

from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import ObjectStore, object_store_from_environment
from nfx.backup.models import BackupKind, BackupSet, BackupState, RestoreOperation, RestoreState
from nfx.certificates.models import Certificate, CertificateState
from nfx.certificates.services import EnvelopeCipher, EnvelopePayload
from nfx.infrastructure.configuration import load_settings
from nfx.infrastructure.schema import schema_status

MANIFEST_VERSION = "backup-v1"
_SAFE_ERROR_CODES = frozenset(
    {
        "capture_failed",
        "database_dump_failed",
        "object_missing",
        "object_divergent",
        "key_unavailable",
        "key_invalid",
        "manifest_invalid",
        "archive_corrupt",
        "insufficient_space",
        "interrupted",
        "live_target",
        "target_invalid",
        "source_unavailable",
    }
)


class BackupError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code if code in _SAFE_ERROR_CODES else "capture_failed"
        super().__init__(self.code)


@dataclass(frozen=True)
class RestoreTarget:
    """An explicitly isolated destination; runtime roots must be supplied."""

    root: Path
    runtime_root: Path | None
    isolated: bool = True
    active_volumes: tuple[Path, ...] = ()


@dataclass(frozen=True)
class RetentionSelection:
    keep: tuple[uuid.UUID, ...]
    expire: tuple[uuid.UUID, ...]


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _digest_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise BackupError("archive_corrupt") from exc
    return size, digest.hexdigest()


def _write_bytes(path: Path, value: bytes) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("wb") as stream:
            stream.write(value)
        path.chmod(0o600)
    except OSError as exc:
        raise BackupError("insufficient_space") from exc
    return len(value), hashlib.sha256(value).hexdigest()


def _database_dump() -> bytes:
    """Produce a deterministic logical PostgreSQL snapshot without CLI secrets."""
    try:
        objects = [
            obj
            for model in apps.get_models()
            if model._meta.app_label == "nfx"
            for obj in model._default_manager.all().order_by("pk")
        ]
        rows = serializers.serialize("json", objects, use_natural_foreign_keys=False)
    except Exception as exc:
        raise BackupError("database_dump_failed") from exc
    return cast(str, rows).encode("utf-8")


def _object_bytes(store: ObjectStore, artifact: Artifact) -> bytes:
    try:
        stream = store.read(artifact.object_key)
    except Exception as exc:
        raise BackupError("source_unavailable") from exc
    if stream is None:
        raise BackupError("object_missing")
    try:
        payload = stream.read()
    finally:
        stream.close()
    if not isinstance(payload, bytes):
        raise BackupError("object_divergent")
    if (
        len(payload) != artifact.size_bytes
        or hashlib.sha256(payload).hexdigest() != artifact.digest
    ):
        raise BackupError("object_divergent")
    return payload


def _model_counts() -> dict[str, int]:
    return {
        f"{model._meta.app_label}.{model._meta.model_name}": model._default_manager.count()
        for model in apps.get_models()
        if model._meta.app_label == "nfx"
    }


def _link_counts() -> dict[str, int]:
    from nfx.documents.models import DocumentEventEvidence, DocumentEvidence

    return {
        "documents_with_artifact": DocumentEvidence.objects.values("document_id")
        .distinct()
        .count(),
        "event_evidence": DocumentEventEvidence.objects.count(),
        "certificates_with_artifact": Certificate.objects.filter(artifact__isnull=False).count(),
    }


def _config_references() -> dict[str, object]:
    settings = load_settings()
    status = schema_status()
    return {
        "profile": settings.public.profile,
        "schema_version": f"nfx:{status.required[-1] if status.required else 'unknown'}",
        "certificate_key_reference": "NFX_CERTIFICATE_MASTER_KEY_FILE|NFX_CERTIFICATE_MASTER_KEY",
        "object_store_reference": "MINIO_ENDPOINT|MINIO_BUCKET",
    }


def _protected_probe(certificate: Certificate, encrypted_pfx: bytes) -> dict[str, object]:
    return {
        "certificate_id": str(certificate.id),
        "key_version": certificate.key_version,
        "encrypted_data_key": base64.b64encode(bytes(certificate.encrypted_data_key)).decode(),
        "data_key_nonce": base64.b64encode(bytes(certificate.data_key_nonce)).decode(),
        "encrypted_password": base64.b64encode(bytes(certificate.encrypted_password)).decode(),
        "password_nonce": base64.b64encode(bytes(certificate.password_nonce)).decode(),
        "encrypted_pfx": base64.b64encode(encrypted_pfx).decode(),
    }


def _validate_probe(probe: Mapping[str, object], master_key: bytes) -> None:
    try:
        certificate_id = uuid.UUID(str(probe["certificate_id"]))
        payload = EnvelopePayload(
            encrypted_data_key=base64.b64decode(cast(str, probe["encrypted_data_key"])),
            data_key_nonce=base64.b64decode(cast(str, probe["data_key_nonce"])),
            encrypted_password=base64.b64decode(cast(str, probe["encrypted_password"])),
            password_nonce=base64.b64decode(cast(str, probe["password_nonce"])),
            encrypted_pfx=base64.b64decode(cast(str, probe["encrypted_pfx"])),
        )
        material = EnvelopeCipher(master_key, int(cast(str, probe["key_version"]))).decrypt(
            certificate_id, payload
        )
    except Exception as exc:
        raise BackupError("key_invalid") from exc
    finally:
        if "material" in locals():
            material[0][:] = b"\\x00" * len(material[0])
            material[1][:] = b"\\x00" * len(material[1])


def _target_reference(root: Path) -> str:
    return hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:24]


def validate_isolated_target(target: RestoreTarget, *, backup_root: Path) -> None:
    if not target.isolated or target.runtime_root is None:
        raise BackupError("live_target")
    root, runtime = target.root, target.runtime_root
    if not root.is_absolute() or not runtime.is_absolute():
        raise BackupError("target_invalid")
    try:
        root, runtime, backup = root.resolve(), runtime.resolve(), backup_root.resolve()
        if root == runtime or root in runtime.parents or runtime in root.parents:
            raise BackupError("live_target")
        if root == backup or root in backup.parents:
            raise BackupError("target_invalid")
        for volume in target.active_volumes:
            resolved = volume.resolve()
            if root == resolved or root in resolved.parents:
                raise BackupError("live_target")
    except OSError as exc:
        raise BackupError("target_invalid") from exc
    if root.exists() and not root.is_dir():
        raise BackupError("target_invalid")


def select_retention(
    backups: Iterable[BackupSet], *, daily: int = 7, weekly: int = 4, monthly: int = 12
) -> RetentionSelection:
    """Keep newest complete sets independently by their declared schedule kind."""
    limits = {"daily": daily, "weekly": weekly, "monthly": monthly}
    ordered = sorted(backups, key=lambda item: (item.started_at, str(item.id)), reverse=True)
    seen = {kind: 0 for kind in limits}
    keep: list[uuid.UUID] = []
    expire: list[uuid.UUID] = []
    for backup in ordered:
        if backup.state != BackupState.COMPLETE or backup.kind not in limits:
            continue
        if seen[backup.kind] < limits[backup.kind]:
            keep.append(backup.id)
            seen[backup.kind] += 1
        else:
            expire.append(backup.id)
    return RetentionSelection(tuple(keep), tuple(expire))


class BackupService:
    def __init__(
        self,
        *,
        backup_root: Path | None = None,
        object_store: ObjectStore | None = None,
        master_key: bytes | None = None,
        clock: Callable[[], datetime] = timezone.now,
    ) -> None:
        self.backup_root = backup_root or Path(load_settings().operational.backup_root)
        self.object_store = object_store
        self.master_key = master_key
        self.clock = clock

    def _master_key(self) -> bytes:
        if self.master_key is None:
            self.master_key = load_settings().secrets.certificate_master_key
        if len(self.master_key) != 32:
            raise BackupError("key_unavailable")
        return self.master_key

    def create_backup(
        self,
        kind: str,
        *,
        idempotency_key: str = "",
        database_dump: bytes | None = None,
    ) -> BackupSet:
        if kind not in BackupKind.values:
            raise BackupError("capture_failed")
        if idempotency_key:
            existing = BackupSet.objects.filter(idempotency_key=idempotency_key).first()
            if existing is not None:
                return existing
        backup = BackupSet.objects.create(
            kind=kind,
            state=BackupState.RUNNING,
            version=MANIFEST_VERSION,
            idempotency_key=idempotency_key,
            started_at=self.clock(),
        )
        staging = self.backup_root / f".{backup.id}.partial"
        final = self.backup_root / str(backup.id)
        try:
            staging.mkdir(parents=True, exist_ok=False)
            db_payload = database_dump if database_dump is not None else _database_dump()
            db_size, db_digest = _write_bytes(staging / "database.dump", db_payload)
            store = self.object_store or cast(ObjectStore, object_store_from_environment())
            entries: list[dict[str, object]] = []
            total_size = 0
            for artifact in Artifact.objects.filter(state=ArtifactState.FINALIZED).order_by("id"):
                payload = _object_bytes(store, artifact)
                relative = f"objects/{artifact.id}.bin"
                size, digest = _write_bytes(staging / relative, payload)
                entries.append(
                    {
                        "artifact_id": str(artifact.id),
                        "logical_class": artifact.logical_class,
                        "relative_path": relative,
                        "size_bytes": size,
                        "digest": digest,
                    }
                )
                total_size += size
            probes: list[dict[str, object]] = []
            for certificate in Certificate.objects.filter(
                state=CertificateState.CURRENT, artifact__isnull=False
            ).select_related("artifact"):
                if certificate.artifact is None:
                    raise BackupError("key_unavailable")
                encrypted_pfx = _object_bytes(store, certificate.artifact)
                probe = _protected_probe(certificate, encrypted_pfx)
                _validate_probe(probe, self._master_key())
                relative = f"a1/{certificate.id}.json"
                _write_bytes(staging / relative, _canonical(probe))
                probes.append(
                    {
                        "certificate_id": str(certificate.id),
                        "key_version": certificate.key_version,
                    }
                )
            manifest: dict[str, object] = {
                "manifest_version": MANIFEST_VERSION,
                "backup_id": str(backup.id),
                "kind": kind,
                "created_at": backup.started_at.isoformat(),
                "database": {
                    "relative_path": "database.dump",
                    "size_bytes": db_size,
                    "digest": db_digest,
                    "counts": _model_counts(),
                },
                "objects": {
                    "count": len(entries),
                    "total_size_bytes": total_size,
                    "entries": entries,
                },
                "certificates": {
                    "count": len(probes),
                    "key_versions": sorted(
                        {int(cast(str, item["key_version"])) for item in probes}
                    ),
                    "probes": probes,
                },
                "links": _link_counts(),
                "configuration": _config_references(),
            }
            manifest_hash = hashlib.sha256(_canonical(manifest)).hexdigest()
            _write_bytes(staging / "manifest.json", _canonical(manifest))
            staging.rename(final)
            size_bytes = sum(_digest_file(path)[0] for path in final.rglob("*") if path.is_file())
            backup.state = BackupState.COMPLETE
            backup.backup_path, backup.manifest, backup.manifest_hash = (
                str(final),
                manifest,
                manifest_hash,
            )
            backup.size_bytes, backup.completed_at = size_bytes, self.clock()
            backup.save(
                update_fields=[
                    "state",
                    "backup_path",
                    "manifest",
                    "manifest_hash",
                    "size_bytes",
                    "completed_at",
                ]
            )
            return backup
        except BackupError as exc:
            self._fail_backup(backup, exc.code)
            shutil.rmtree(staging, ignore_errors=True)
            return backup
        except (OSError, ValueError, TypeError) as exc:
            self._fail_backup(backup, "capture_failed")
            shutil.rmtree(staging, ignore_errors=True)
            del exc
            return backup

    def _fail_backup(self, backup: BackupSet, code: str) -> None:
        backup.state = BackupState.FAILED if backup.manifest is None else BackupState.PARTIAL
        backup.safe_error = code if code in _SAFE_ERROR_CODES else "capture_failed"
        backup.completed_at = self.clock()
        backup.save(update_fields=["state", "safe_error", "completed_at"])

    def expire(self) -> RetentionSelection:
        selection = select_retention(BackupSet.objects.all())
        for backup_id in selection.expire:
            backup = BackupSet.objects.filter(pk=backup_id, state=BackupState.COMPLETE).first()
            if backup is None:
                continue
            try:
                if backup.backup_path:
                    shutil.rmtree(backup.backup_path)
            except FileNotFoundError:
                pass
            except OSError:
                continue
            backup.state, backup.backup_path = BackupState.EXPIRED, ""
            backup.save(update_fields=["state", "backup_path"])
        return selection

    def restore(
        self, backup_id: str | uuid.UUID, target: RestoreTarget, *, master_key: bytes | None = None
    ) -> RestoreOperation:
        backup = BackupSet.objects.get(pk=backup_id)
        operation = RestoreOperation.objects.create(
            backup=backup,
            target_reference=_target_reference(target.root),
            state=RestoreState.RUNNING,
            started_at=self.clock(),
        )
        try:
            validate_isolated_target(target, backup_root=self.backup_root)
            if (
                backup.state != BackupState.COMPLETE
                or not backup.backup_path
                or backup.manifest is None
            ):
                raise BackupError("source_unavailable")
            source = Path(backup.backup_path)
            if not source.is_dir():
                raise BackupError("source_unavailable")
            manifest_path = source / "manifest.json"
            if _digest_file(manifest_path)[1] != backup.manifest_hash:
                raise BackupError("manifest_invalid")
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if loaded != backup.manifest:
                raise BackupError("manifest_invalid")
            db = cast(dict[str, object], loaded["database"])
            db_path = source / cast(str, db["relative_path"])
            if _digest_file(db_path) != (
                int(cast(str, db["size_bytes"])),
                str(db["digest"]),
            ):
                raise BackupError("archive_corrupt")
            objects = cast(dict[str, object], loaded["objects"])
            for entry in cast(list[dict[str, object]], objects["entries"]):
                object_path = source / cast(str, entry["relative_path"])
                if _digest_file(object_path) != (
                    int(cast(str, entry["size_bytes"])),
                    str(entry["digest"]),
                ):
                    raise BackupError("archive_corrupt")
            certificates = cast(dict[str, object], loaded["certificates"])
            if int(cast(str, certificates["count"])) > 0:
                key = master_key or self._master_key()
                for entry in cast(list[dict[str, object]], certificates["probes"]):
                    probe_path = source / f"a1/{entry['certificate_id']}.json"
                    _validate_probe(
                        cast(Mapping[str, object], json.loads(probe_path.read_text())), key
                    )
                a1_status = "verified"
            else:
                a1_status = "not_applicable"
            target.root.mkdir(parents=True, exist_ok=True)
            if any(target.root.iterdir()):
                raise BackupError("target_invalid")
            shutil.copytree(source, target.root, dirs_exist_ok=True)
            validations = {
                "manifest": "verified",
                "schema_version": cast(dict[str, object], loaded["configuration"])[
                    "schema_version"
                ],
                "database": {"hash": "verified", "counts": db["counts"]},
                "objects": {"hashes": "verified", "count": objects["count"]},
                "links": loaded["links"],
                "audit_jobs_cursors": "included",
                "a1_decryption": a1_status,
                "isolated_target": True,
            }
            (target.root / "restore-report.json").write_bytes(_canonical(validations))
            operation.state, operation.validations = RestoreState.SUCCESS, validations
            operation.completed_at = self.clock()
            operation.save(update_fields=["state", "validations", "completed_at"])
        except BackupError as exc:
            operation.state, operation.safe_error = RestoreState.FAILED, exc.code
            operation.completed_at = self.clock()
            operation.save(update_fields=["state", "safe_error", "completed_at"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            operation.state, operation.safe_error = RestoreState.FAILED, "archive_corrupt"
            operation.completed_at = self.clock()
            operation.save(update_fields=["state", "safe_error", "completed_at"])
            del exc
        return operation

    def status(self, *, now: datetime | None = None) -> dict[str, object]:
        current = now or self.clock()
        latest = (
            BackupSet.objects.exclude(state=BackupState.EXPIRED)
            .order_by("-started_at", "-id")
            .first()
        )
        latest_success = (
            BackupSet.objects.filter(state=BackupState.COMPLETE).order_by("-completed_at").first()
        )
        restore = RestoreOperation.objects.order_by("-started_at", "-id").first()
        age = (
            max(0.0, (current - latest_success.completed_at).total_seconds())
            if latest_success and latest_success.completed_at
            else None
        )
        return {
            "status": "success" if latest_success else ("failure" if latest else "unavailable"),
            "latest_backup": {
                "id": str(latest.id) if latest else None,
                "state": latest.state if latest else None,
                "kind": latest.kind if latest else None,
                "completed_at": latest.completed_at.isoformat()
                if latest and latest.completed_at
                else None,
                "size_bytes": latest.size_bytes if latest else None,
                "manifest_hash": latest.manifest_hash if latest else None,
                "safe_error": latest.safe_error if latest else "",
            },
            "latest_success_age_seconds": age,
            "retention": {
                "daily": BackupSet.objects.filter(
                    kind=BackupKind.DAILY, state=BackupState.COMPLETE
                ).count(),
                "weekly": BackupSet.objects.filter(
                    kind=BackupKind.WEEKLY, state=BackupState.COMPLETE
                ).count(),
                "monthly": BackupSet.objects.filter(
                    kind=BackupKind.MONTHLY, state=BackupState.COMPLETE
                ).count(),
            },
            "latest_restore": {
                "id": str(restore.id) if restore else None,
                "state": restore.state if restore else None,
                "completed_at": restore.completed_at.isoformat()
                if restore and restore.completed_at
                else None,
                "safe_error": restore.safe_error if restore else "",
            },
        }


def backup_status(*, now: datetime | None = None) -> dict[str, object]:
    return BackupService().status(now=now)
