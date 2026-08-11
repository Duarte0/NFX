from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q

from nfx.artifacts.models import Artifact
from nfx.documents.models import Document
from nfx.identity.models import User
from nfx.jobs.models import Job


class ExportState(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETE = "complete", "Complete"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"
    AVAILABLE = "available", "Available"
    EXPIRED = "expired", "Expired"
    EXCLUDED = "excluded", "Excluded"


class ExportItemState(models.TextChoices):
    PENDING = "pending", "Pending"
    INCLUDED = "included", "Included"
    MISSING = "missing", "Missing"
    DIVERGENT = "divergent", "Divergent"
    FAILED = "failed", "Failed"
    EXCLUDED = "excluded", "Excluded"


class Export(models.Model):
    """A frozen, temporary export request; fiscal bytes remain artifact-owned."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name="exports")
    filter_snapshot = models.JSONField(default=dict)
    selection_snapshot = models.JSONField(default=dict)
    expected_count = models.PositiveIntegerField(default=0)
    produced_count = models.PositiveIntegerField(default=0)
    expected_bytes = models.BigIntegerField(default=0)
    produced_bytes = models.BigIntegerField(default=0)
    state = models.CharField(
        max_length=16, choices=ExportState.choices, default=ExportState.PENDING
    )
    safe_result = models.JSONField(default=dict)
    safe_error = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    job = models.OneToOneField(
        Job, null=True, blank=True, on_delete=models.PROTECT, related_name="export"
    )
    zip_artifact = models.OneToOneField(
        Artifact, null=True, blank=True, on_delete=models.PROTECT, related_name="zip_export"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nfx_export"
        indexes = [
            models.Index(fields=("requester", "created_at"), name="nfx_export_owner_time_ix"),
            models.Index(fields=("state", "expires_at"), name="nfx_export_expiry_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("requester", "idempotency_key"), name="nfx_export_owner_key_uq"
            ),
            models.CheckConstraint(
                condition=Q(expected_count__gte=0), name="nfx_export_expected_count_ck"
            ),
            models.CheckConstraint(
                condition=Q(produced_count__gte=0), name="nfx_export_produced_count_ck"
            ),
            models.CheckConstraint(
                condition=Q(expected_bytes__gte=0), name="nfx_export_expected_bytes_ck"
            ),
            models.CheckConstraint(
                condition=Q(produced_bytes__gte=0), name="nfx_export_produced_bytes_ck"
            ),
        ]


class ExportItem(models.Model):
    """One frozen document/artifact reference and its safe composition result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    export = models.ForeignKey(Export, on_delete=models.CASCADE, related_name="items")
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="export_items",
    )
    artifact = models.ForeignKey(
        Artifact, null=True, blank=True, on_delete=models.PROTECT, related_name="export_items"
    )
    digest = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=255, blank=True)
    sequence = models.PositiveIntegerField()
    state = models.CharField(
        max_length=16, choices=ExportItemState.choices, default=ExportItemState.PENDING
    )
    archive_path = models.CharField(max_length=255, blank=True)
    safe_error = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_export_item"
        ordering = ("sequence", "id")
        constraints = [
            models.UniqueConstraint(fields=("export", "document"), name="nfx_export_document_uq"),
            models.UniqueConstraint(fields=("export", "sequence"), name="nfx_export_sequence_uq"),
            models.CheckConstraint(condition=Q(size_bytes__gte=0), name="nfx_export_item_size_ck"),
        ]
        indexes = [
            models.Index(fields=("export", "state"), name="nfx_export_item_state_ix"),
        ]
