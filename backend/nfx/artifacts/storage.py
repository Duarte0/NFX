"""Internal S3/MinIO port and artifact lifecycle service.

The service intentionally has no HTTP or business-authorization concerns.  It
is safe to call from a future worker after its caller has authorized the use
case.  PostgreSQL and S3 are not transactional together, so an uploaded object
is only made visible by a later, verified metadata finalization.
"""

from __future__ import annotations

import hashlib
import io
import logging
import time
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import BinaryIO, Protocol

import boto3
from botocore.exceptions import ClientError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from nfx.artifacts.models import Artifact, ArtifactState

logger = logging.getLogger(__name__)

SHA256 = "sha256"
DEFAULT_MAX_SIZE_BYTES = 50 * 1024 * 1024


class ArtifactError(RuntimeError):
    """Safe failure exposed to a caller; never embeds object contents or credentials."""


class ArtifactNotReadable(ArtifactError):
    pass


class ArtifactTooLarge(ArtifactError):
    pass


class ArtifactConflict(ArtifactError):
    pass


@dataclass(frozen=True)
class ObjectMetadata:
    size_bytes: int
    digest: str
    content_type: str


@dataclass(frozen=True)
class ReconciliationReport:
    pending: int
    missing: int
    divergent: int
    orphan_objects: int


@dataclass(frozen=True)
class ArtifactMetrics:
    pending: int
    pending_older_than_limit: int
    missing: int
    divergent: int
    orphan_objects: int


class ObjectStore(Protocol):
    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata: ...

    def head(self, object_key: str) -> ObjectMetadata | None: ...

    def read(self, object_key: str) -> BinaryIO | None: ...

    def list_keys(self, prefix: str) -> Iterator[str]: ...


class S3ObjectStore:
    """The only adapter that knows S3/MinIO credentials and bucket details."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    def write_stream(
        self, object_key: str, chunks: Iterable[bytes], content_type: str, maximum_size: int
    ) -> ObjectMetadata:
        # SpooledTemporaryFile bounds memory while allowing boto3 to stream the
        # upload.  It also lets us send the verified digest as immutable object
        # metadata instead of trusting a caller-supplied checksum.
        import tempfile

        digest = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b") as staged:
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise ArtifactError("Artifact stream must contain bytes")
                size += len(chunk)
                if size > maximum_size:
                    raise ArtifactTooLarge("Artifact exceeds its configured size limit")
                digest.update(chunk)
                staged.write(chunk)
            staged.seek(0)
            self.client.upload_fileobj(
                staged,
                self.bucket,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {"sha256": digest.hexdigest()},
                },
            )
        return ObjectMetadata(size, digest.hexdigest(), content_type)

    def head(self, object_key: str) -> ObjectMetadata | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        metadata = response.get("Metadata", {})
        digest = metadata.get("sha256", "")
        return ObjectMetadata(
            int(response["ContentLength"]),
            digest,
            str(response.get("ContentType", "application/octet-stream")),
        )

    def read(self, object_key: str) -> BinaryIO | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return response["Body"]

    def list_keys(self, prefix: str) -> Iterator[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                yield str(item["Key"])


def object_store_from_environment() -> S3ObjectStore:
    """Build the adapter at the infrastructure edge, not in a domain caller."""
    from nfx.infrastructure.dependencies import dependencies_from_environment

    dependencies = dependencies_from_environment()
    return S3ObjectStore(
        dependencies.minio_endpoint,
        dependencies.minio_access_key,
        dependencies.minio_secret_key,
        dependencies.minio_bucket,
    )


class ArtifactStorageService:
    """Creates pending metadata, verifies bytes, and finalizes atomically."""

    object_prefix = "artifacts/"

    def __init__(self, store: ObjectStore, maximum_size: int = DEFAULT_MAX_SIZE_BYTES) -> None:
        self.store = store
        self.maximum_size = maximum_size

    def begin(self, logical_class: str, logical_key: str, declared_mime_type: str) -> Artifact:
        if not logical_class or not logical_key or not declared_mime_type:
            raise ArtifactError("Artifact class, logical key, and MIME type are required")
        if len(logical_class) > 64 or len(logical_key) > 255 or len(declared_mime_type) > 255:
            raise ArtifactError("Artifact metadata exceeds its configured limit")
        artifact_id = uuid.uuid4()
        # This opaque generated value is intentionally independent of caller input.
        object_key = f"{self.object_prefix}{artifact_id.hex}/v1"
        return Artifact.objects.create(
            id=artifact_id,
            logical_class=logical_class,
            logical_key=logical_key,
            object_key=object_key,
            declared_mime_type=declared_mime_type,
        )

    def transmit(self, artifact_id: uuid.UUID, chunks: Iterable[bytes]) -> Artifact:
        artifact = Artifact.objects.get(pk=artifact_id)
        if artifact.state != ArtifactState.PENDING:
            raise ArtifactError("Only a pending artifact can receive bytes")
        started = time.monotonic()
        try:
            written = self.store.write_stream(
                artifact.object_key, chunks, artifact.declared_mime_type, self.maximum_size
            )
            verified = self.store.head(artifact.object_key)
            if verified is None or verified.size_bytes != written.size_bytes or verified.digest != written.digest:
                raise ArtifactError("Object storage integrity verification failed")
            finalized = self._finalize(artifact_id, written, verified)
        except Exception as exc:
            logger.info(
                "artifact_transmit_finished",
                extra={
                    "artifact_id": str(artifact_id),
                    "operation": "transmit",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "result": "failure",
                },
            )
            if isinstance(exc, ArtifactError):
                raise
            raise ArtifactError("Object storage write failed") from exc
        logger.info(
            "artifact_transmit_finished",
            extra={
                "artifact_id": str(artifact_id),
                "operation": "transmit",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "size_bytes": finalized.size_bytes,
                "result": "success",
            },
        )
        return finalized

    def _finalize(
        self, artifact_id: uuid.UUID, written: ObjectMetadata, verified: ObjectMetadata
    ) -> Artifact:
        try:
            with transaction.atomic():
                artifact = Artifact.objects.select_for_update().get(pk=artifact_id)
                if artifact.state == ArtifactState.FINALIZED:
                    if artifact.digest == written.digest and artifact.size_bytes == written.size_bytes:
                        return artifact
                    raise ArtifactConflict("Finalized artifact metadata conflicts with retry")
                if artifact.state != ArtifactState.PENDING:
                    raise ArtifactError("Artifact cannot be finalized from its current state")
                artifact.digest_algorithm = SHA256
                artifact.digest = written.digest
                artifact.size_bytes = written.size_bytes
                artifact.detected_mime_type = verified.content_type
                artifact.state = ArtifactState.FINALIZED
                artifact.finalized_at = timezone.now()
                artifact.safe_error = ""
                artifact.save()
                return artifact
        except IntegrityError as exc:
            existing = Artifact.objects.filter(
                logical_key=Artifact.objects.get(pk=artifact_id).logical_key,
                state=ArtifactState.FINALIZED,
            ).first()
            if existing and existing.digest == written.digest and existing.size_bytes == written.size_bytes:
                return existing
            raise ArtifactConflict("A different finalized artifact already owns this logical key") from exc

    def open_verified(self, artifact_id: uuid.UUID) -> BinaryIO:
        artifact = Artifact.objects.get(pk=artifact_id)
        if artifact.state != ArtifactState.FINALIZED:
            raise ArtifactNotReadable("Artifact is not available for reading")
        stream = self.store.read(artifact.object_key)
        if stream is None:
            self._mark_problem(artifact, ArtifactState.MISSING, "Object missing from storage")
            raise ArtifactNotReadable("Artifact is not available for reading")
        try:
            payload = stream.read()
        finally:
            stream.close()
        if len(payload) != artifact.size_bytes or hashlib.sha256(payload).hexdigest() != artifact.digest:
            self._mark_problem(artifact, ArtifactState.DIVERGENT, "Object integrity diverged")
            raise ArtifactNotReadable("Artifact is not available for reading")
        return io.BytesIO(payload)

    def _mark_problem(self, artifact: Artifact, state: str, error: str) -> None:
        Artifact.objects.filter(pk=artifact.pk, state=ArtifactState.FINALIZED).update(
            state=state, safe_error=error, updated_at=timezone.now()
        )

    def reconcile(self) -> ReconciliationReport:
        referenced = set(Artifact.objects.values_list("object_key", flat=True))
        orphan_objects = sum(1 for key in self.store.list_keys(self.object_prefix) if key not in referenced)
        pending = Artifact.objects.filter(state=ArtifactState.PENDING).count()
        missing = divergent = 0
        for artifact in Artifact.objects.filter(state=ArtifactState.FINALIZED).iterator():
            metadata = self.store.head(artifact.object_key)
            if metadata is None:
                self._mark_problem(artifact, ArtifactState.MISSING, "Object missing from storage")
                missing += 1
            elif metadata.size_bytes != artifact.size_bytes or metadata.digest != artifact.digest:
                self._mark_problem(artifact, ArtifactState.DIVERGENT, "Object integrity diverged")
                divergent += 1
        return ReconciliationReport(pending, missing, divergent, orphan_objects)

    def metrics(self, pending_age: timedelta = timedelta(hours=1)) -> ArtifactMetrics:
        threshold = timezone.now() - pending_age
        states = dict(
            Artifact.objects.values("state").annotate(total=Count("id")).values_list("state", "total")
        )
        referenced = set(Artifact.objects.values_list("object_key", flat=True))
        return ArtifactMetrics(
            pending=states.get(ArtifactState.PENDING, 0),
            pending_older_than_limit=Artifact.objects.filter(
                state=ArtifactState.PENDING, created_at__lt=threshold
            ).count(),
            missing=states.get(ArtifactState.MISSING, 0),
            divergent=states.get(ArtifactState.DIVERGENT, 0),
            orphan_objects=sum(1 for key in self.store.list_keys(self.object_prefix) if key not in referenced),
        )
