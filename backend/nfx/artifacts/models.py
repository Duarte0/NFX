from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class ArtifactState(models.TextChoices):
    PENDING = "pending", "Pending"
    FINALIZED = "finalized", "Finalized"
    MISSING = "missing", "Missing"
    DIVERGENT = "divergent", "Divergent"


class Artifact(models.Model):
    """Relational reference to one opaque object-store key.

    The logical key belongs to a caller and is never used as an object-store
    name.  Future document/certificate/export modules reference this model by
    its internal UUID.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    logical_class = models.CharField(max_length=64)
    logical_key = models.CharField(max_length=255)
    object_key = models.CharField(max_length=255, unique=True)
    digest_algorithm = models.CharField(max_length=16, default="sha256")
    digest = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    declared_mime_type = models.CharField(max_length=255)
    detected_mime_type = models.CharField(max_length=255, blank=True)
    state = models.CharField(
        max_length=16, choices=ArtifactState.choices, default=ArtifactState.PENDING
    )
    version = models.PositiveIntegerField(default=1)
    safe_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(size_bytes__isnull=True) | Q(size_bytes__gte=0),
                name="nfx_artifact_size_nonnegative_ck",
            ),
            models.UniqueConstraint(
                fields=("logical_key",),
                condition=Q(state=ArtifactState.FINALIZED),
                name="nfx_artifact_one_finalized_logical_key_uq",
            ),
        ]
        indexes = [
            models.Index(fields=("state", "created_at"), name="nfx_artifact_state_age_ix"),
            models.Index(fields=("object_key",), name="nfx_artifact_object_key_ix"),
        ]
