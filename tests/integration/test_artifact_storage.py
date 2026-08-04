from __future__ import annotations

import hashlib
import io
import threading
from collections.abc import Iterable, Iterator

import pytest
from django.db import IntegrityError

from nfx.artifacts.models import Artifact, ArtifactState
from nfx.artifacts.storage import (
    ArtifactConflict,
    ArtifactNotReadable,
    ArtifactStorageService,
    ArtifactTooLarge,
    ObjectMetadata,
    S3ObjectStore,
)


class MemoryObjectStore:
    """Synthetic isolated object store; it deliberately exposes fault injection."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_writes = False

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        if self.fail_writes:
            raise OSError("synthetic object-store outage")
        result = bytearray()
        for chunk in chunks:
            if not isinstance(chunk, bytes):
                raise TypeError("synthetic invalid stream")
            result.extend(chunk)
            if len(result) > maximum_size:
                raise ArtifactTooLarge("Artifact exceeds its configured size limit")
        payload = bytes(result)
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
def store() -> MemoryObjectStore:
    return MemoryObjectStore()


@pytest.fixture
def service(store: MemoryObjectStore) -> ArtifactStorageService:
    return ArtifactStorageService(store, maximum_size=8)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("payload", [b"", b"eight!!!"])
def test_finalization_requires_verified_hash_and_size(
    service: ArtifactStorageService, payload: bytes
) -> None:
    artifact = service.begin("synthetic", f"key-{len(payload)}", "application/octet-stream")

    finalized = service.transmit(artifact.id, [payload[:3], payload[3:]])

    assert finalized.state == ArtifactState.FINALIZED
    assert finalized.size_bytes == len(payload)
    assert finalized.digest == hashlib.sha256(payload).hexdigest()
    assert finalized.object_key.startswith("artifacts/")
    assert "key-" not in finalized.object_key
    assert service.open_verified(finalized.id).read() == payload


@pytest.mark.django_db(transaction=True)
def test_limit_interrupted_upload_and_outage_leave_a_retryable_pending_reference(
    service: ArtifactStorageService, store: MemoryObjectStore
) -> None:
    oversized = service.begin("synthetic", "limit", "application/octet-stream")
    with pytest.raises(ArtifactTooLarge):
        service.transmit(oversized.id, [b"012345678"])
    assert Artifact.objects.get(pk=oversized.id).state == ArtifactState.PENDING

    interrupted = service.begin("synthetic", "outage", "application/octet-stream")
    store.fail_writes = True
    with pytest.raises(Exception):
        service.transmit(interrupted.id, [b"data"])
    assert Artifact.objects.get(pk=interrupted.id).state == ArtifactState.PENDING

    store.fail_writes = False
    assert service.transmit(interrupted.id, [b"data"]).state == ArtifactState.FINALIZED


@pytest.mark.django_db(transaction=True)
def test_db_failure_after_upload_leaves_a_detectable_pending_reference(
    service: ArtifactStorageService, store: MemoryObjectStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = service.begin("synthetic", "db-failure", "application/octet-stream")

    def fail_finalize(*args: object, **kwargs: object) -> Artifact:
        raise IntegrityError("synthetic database failure")

    monkeypatch.setattr(service, "_finalize", fail_finalize)
    with pytest.raises(Exception):
        service.transmit(artifact.id, [b"data"])

    assert Artifact.objects.get(pk=artifact.id).state == ArtifactState.PENDING
    assert artifact.object_key in store.objects
    report = service.reconcile()
    assert report.pending == 1  # a known pending reference is not deleted or misreported as an orphan
    assert artifact.object_key in store.objects


@pytest.mark.django_db(transaction=True)
def test_missing_and_altered_objects_are_never_served_and_reconciliation_preserves_evidence(
    service: ArtifactStorageService, store: MemoryObjectStore
) -> None:
    missing = service.begin("synthetic", "missing", "application/octet-stream")
    divergent = service.begin("synthetic", "divergent", "application/octet-stream")
    service.transmit(missing.id, [b"missing"])
    service.transmit(divergent.id, [b"original"])
    del store.objects[missing.object_key]
    store.objects[divergent.object_key] = (b"altered", "application/octet-stream")

    report = service.reconcile()

    assert (report.missing, report.divergent) == (1, 1)
    assert Artifact.objects.get(pk=missing.id).state == ArtifactState.MISSING
    assert Artifact.objects.get(pk=divergent.id).state == ArtifactState.DIVERGENT
    with pytest.raises(ArtifactNotReadable):
        service.open_verified(missing.id)
    with pytest.raises(ArtifactNotReadable):
        service.open_verified(divergent.id)
    assert divergent.object_key in store.objects


@pytest.mark.django_db(transaction=True)
def test_reconciler_reports_orphans_without_deleting_them(
    service: ArtifactStorageService, store: MemoryObjectStore
) -> None:
    store.objects["artifacts/orphan/v1"] = (b"orphan", "application/octet-stream")

    report = service.reconcile()

    assert report.orphan_objects == 1
    assert "artifacts/orphan/v1" in store.objects
    metrics = service.metrics()
    assert metrics.orphan_objects == 1


@pytest.mark.django_db(transaction=True)
def test_finalized_logical_key_is_idempotent_for_same_bytes_and_conflicts_for_different_bytes(
    service: ArtifactStorageService
) -> None:
    first = service.begin("synthetic", "retry", "application/octet-stream")
    same = service.begin("synthetic", "retry", "application/octet-stream")
    different = service.begin("synthetic", "retry", "application/octet-stream")
    first = service.transmit(first.id, [b"same"])

    assert service.transmit(same.id, [b"same"]).id == first.id
    with pytest.raises(ArtifactConflict):
        service.transmit(different.id, [b"diff"])
    assert Artifact.objects.filter(logical_key="retry", state=ArtifactState.FINALIZED).count() == 1


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_finalizations_cannot_create_two_finalized_references(
    service: ArtifactStorageService
) -> None:
    first = service.begin("synthetic", "concurrent", "application/octet-stream")
    second = service.begin("synthetic", "concurrent", "application/octet-stream")
    failures: list[BaseException] = []

    def transmit(artifact_id: object) -> None:
        try:
            service.transmit(artifact_id, [b"same"])
        except BaseException as exc:  # pragma: no cover - asserted below
            failures.append(exc)

    threads = [threading.Thread(target=transmit, args=(artifact.id,)) for artifact in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not failures
    assert Artifact.objects.filter(logical_key="concurrent", state=ArtifactState.FINALIZED).count() == 1


@pytest.mark.django_db(transaction=True)
def test_minio_adapter_writes_and_verifies_synthetic_bytes() -> None:
    """Exercise the production S3 adapter against the isolated Compose bucket."""
    from nfx.infrastructure.dependencies import dependencies_from_environment

    dependencies = dependencies_from_environment()
    store = S3ObjectStore(
        dependencies.minio_endpoint,
        dependencies.minio_access_key,
        dependencies.minio_secret_key,
        dependencies.minio_bucket,
    )
    object_key = f"artifacts/integration-{__name__.replace('.', '-')}/v1"
    try:
        written = store.write_stream(object_key, [b"synthetic", b"-bytes"], "application/octet-stream", 64)
        assert store.head(object_key) == written
        assert store.read(object_key).read() == b"synthetic-bytes"  # type: ignore[union-attr]
    finally:
        store.client.delete_object(Bucket=dependencies.minio_bucket, Key=object_key)
