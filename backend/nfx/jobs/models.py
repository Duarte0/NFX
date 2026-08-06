# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class JobState(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"


class Job(models.Model):
    """A safe, referential unit of background work and its current lease."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=100)
    logical_target = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    idempotency_key = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField()
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=16, choices=JobState.choices, default=JobState.QUEUED)
    lease_owner = models.CharField(max_length=128, null=True, blank=True)
    lease_issued_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    safe_result = models.JSONField(null=True, blank=True)
    safe_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nfx_job"
        indexes = [
            models.Index(
                fields=("state", "scheduled_at", "-priority"), name="nfx_job_claim_ix"
            ),
            models.Index(fields=("state", "lease_expires_at"), name="nfx_job_expired_lease_ix"),
            models.Index(fields=("logical_target", "created_at"), name="nfx_job_target_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("idempotency_key",),
                condition=~Q(state=JobState.COMPLETED),
                name="nfx_job_active_idempotency_uq",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(state=JobState.RUNNING)
                    | (
                        Q(lease_owner__isnull=False)
                        & Q(lease_issued_at__isnull=False)
                        & Q(lease_expires_at__isnull=False)
                    )
                ),
                name="nfx_job_running_lease_ck",
            ),
            models.CheckConstraint(
                condition=Q(attempt_count__gte=0), name="nfx_job_attempt_nonnegative_ck"
            ),
        ]
