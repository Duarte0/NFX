from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class BackupKind(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class BackupState(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETE = "complete", "Complete"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"


class RestoreState(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class BackupSet(models.Model):
    """Durable metadata for one immutable backup archive."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=8, choices=BackupKind.choices)
    state = models.CharField(max_length=16, choices=BackupState.choices)
    version = models.CharField(max_length=32, default="backup-v1")
    idempotency_key = models.CharField(max_length=255, blank=True)
    backup_path = models.CharField(max_length=1024, blank=True)
    manifest = models.JSONField(null=True, blank=True)
    manifest_hash = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    safe_error = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nfx_backup_set"
        indexes = [
            models.Index(fields=("state", "started_at"), name="nfx_backup_state_time_ix"),
            models.Index(fields=("kind", "started_at"), name="nfx_backup_kind_time_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("idempotency_key",),
                condition=~Q(idempotency_key=""),
                name="nfx_backup_idempotency_uq",
            ),
            models.CheckConstraint(
                condition=Q(size_bytes__gte=0), name="nfx_backup_size_nonnegative_ck"
            ),
            models.CheckConstraint(
                condition=Q(manifest_hash="") | Q(manifest_hash__regex=r"^[a-f0-9]{64}$"),
                name="nfx_backup_manifest_hash_ck",
            ),
        ]


class RestoreOperation(models.Model):
    """Safe evidence for a restore validation into an isolated target."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backup = models.ForeignKey(
        BackupSet, on_delete=models.PROTECT, related_name="restore_operations"
    )
    target_reference = models.CharField(max_length=255)
    state = models.CharField(max_length=16, choices=RestoreState.choices)
    validations = models.JSONField(default=dict)
    safe_error = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nfx_restore_operation"
        indexes = [
            models.Index(fields=("state", "started_at"), name="nfx_restore_state_time_ix"),
            models.Index(fields=("backup", "started_at"), name="nfx_restore_backup_time_ix"),
        ]
