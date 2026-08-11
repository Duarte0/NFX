from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q

from nfx.identity.models import User
from nfx.jobs.models import Job


class DeletionOperationState(models.TextChoices):
    PENDING = "pending", "Pending"
    EXECUTING = "executing", "Executing"
    RECOVERY_REQUIRED = "recovery_required", "Recovery required"
    FAILED = "failed", "Failed"
    COMPLETED = "completed", "Completed"


class DeletionItemState(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    RECOVERY_REQUIRED = "recovery_required", "Recovery required"
    FAILED = "failed", "Failed"


class DeletionItemKind(models.TextChoices):
    DOCUMENT = "document", "Document"
    EVENT = "event", "Event"
    EVIDENCE = "evidence", "Evidence"
    EVENT_EVIDENCE = "event_evidence", "Event evidence"
    RENDER = "render", "Derived render"
    ARTIFACT = "artifact", "Artifact"


class DeletionOperation(models.Model):
    """Durable administrative intent and checkpoint for one document deletion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_document_id = models.UUIDField()
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deletion_operations",
    )
    job = models.ForeignKey(
        Job,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deletion_operations",
    )
    scope_hash = models.CharField(max_length=64)
    scope_version = models.CharField(max_length=32)
    reason = models.CharField(max_length=1000)
    correlation_id = models.CharField(max_length=128)
    state = models.CharField(
        max_length=24,
        choices=DeletionOperationState.choices,
        default=DeletionOperationState.PENDING,
    )
    current_step = models.CharField(max_length=32, blank=True)
    checkpoint = models.JSONField(default=dict)
    safe_error = models.CharField(max_length=64, blank=True)
    result_code = models.CharField(max_length=64, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_deletion_operation"
        indexes = [
            models.Index(
                fields=("target_document_id", "state"), name="nfx_delete_target_state_ix"
            ),
            models.Index(fields=("state", "requested_at"), name="nfx_delete_state_time_ix"),
            models.Index(fields=("actor", "requested_at"), name="nfx_delete_actor_time_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("target_document_id",),
                condition=Q(
                    state__in=(
                        DeletionOperationState.PENDING,
                        DeletionOperationState.EXECUTING,
                        DeletionOperationState.RECOVERY_REQUIRED,
                    )
                ),
                name="nfx_delete_active_target_uq",
            ),
            models.CheckConstraint(
                condition=Q(scope_hash__regex=r"^[a-f0-9]{64}$"),
                name="nfx_delete_scope_hash_ck",
            ),
            models.CheckConstraint(
                condition=Q(scope_version="scope-v1"), name="nfx_delete_scope_version_ck"
            ),
            models.CheckConstraint(
                condition=Q(reason__gt=""), name="nfx_delete_reason_ck"
            ),
        ]


class DeletionItem(models.Model):
    """One safe ID/checkpoint in an operation's immutable deletion set."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation = models.ForeignKey(
        DeletionOperation, on_delete=models.CASCADE, related_name="items"
    )
    kind = models.CharField(max_length=24, choices=DeletionItemKind.choices)
    target_id = models.UUIDField()
    artifact_id = models.UUIDField(null=True, blank=True)
    digest_prefix = models.CharField(max_length=16, blank=True)
    expected_size_bytes = models.BigIntegerField(null=True, blank=True)
    expected_version = models.PositiveIntegerField(null=True, blank=True)
    state = models.CharField(
        max_length=24, choices=DeletionItemState.choices, default=DeletionItemState.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    safe_error = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nfx_deletion_item"
        indexes = [
            models.Index(fields=("operation", "state"), name="nfx_delete_item_state_ix"),
            models.Index(fields=("artifact_id", "state"), name="nfx_delete_item_artifact_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("operation", "kind", "target_id"), name="nfx_delete_item_target_uq"
            ),
            models.CheckConstraint(
                condition=Q(expected_size_bytes__isnull=True) | Q(expected_size_bytes__gte=0),
                name="nfx_delete_item_size_ck",
            ),
            models.CheckConstraint(
                condition=Q(expected_version__isnull=True) | Q(expected_version__gt=0),
                name="nfx_delete_item_version_ck",
            ),
            models.CheckConstraint(
                condition=Q(digest_prefix="") | Q(digest_prefix__regex=r"^[a-f0-9]{16}$"),
                name="nfx_delete_item_digest_ck",
            ),
        ]
