# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid
from typing import Any

from django.db import models
from django.db.models import Q


class JobState(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    BLOCKED = "blocked", "Blocked"


class JobOutcomeKind(models.TextChoices):
    SUCCESS = "success", "Success"
    TEMPORARY = "temporary", "Temporary"
    COOLDOWN = "cooldown", "Cooldown"
    PERMANENT = "permanent", "Permanent"
    PARTIAL = "partial", "Partial"


class JobPolicy(models.Model):
    """Versioned retry policy selected by a job and retained for its lifetime."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_scope = models.CharField(max_length=100)
    flow_scope = models.CharField(max_length=100)
    version = models.PositiveIntegerField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    retry_limit = models.PositiveIntegerField(default=3)
    backoff_initial_seconds = models.PositiveIntegerField(default=1)
    backoff_cap_seconds = models.PositiveIntegerField(default=3600)
    jitter_seconds = models.PositiveIntegerField(default=0)
    cooldown_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Keep effective policy versions immutable after they are published."""
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("job policies are immutable")
        super().save(*args, **kwargs)

    class Meta:
        db_table = "nfx_job_policy"
        indexes = [
            models.Index(
                fields=("source_scope", "flow_scope", "valid_from"),
                name="nfx_policy_scope_valid_ix",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("source_scope", "flow_scope", "version"),
                name="nfx_policy_scope_version_uq",
            ),
            models.CheckConstraint(
                condition=(Q(valid_until__isnull=True) | Q(valid_until__gt=models.F("valid_from"))),
                name="nfx_policy_validity_order_ck",
            ),
            models.CheckConstraint(
                condition=Q(backoff_cap_seconds__gte=models.F("backoff_initial_seconds")),
                name="nfx_policy_backoff_cap_ck",
            ),
            models.CheckConstraint(
                condition=(
                    Q(retry_limit__gte=0)
                    & Q(backoff_initial_seconds__gt=0)
                    & Q(backoff_cap_seconds__gt=0)
                    & Q(jitter_seconds__gte=0)
                    & Q(cooldown_seconds__gte=0)
                ),
                name="nfx_policy_timing_values_ck",
            ),
        ]


class Job(models.Model):
    """A safe, referential unit of background work and its current lease."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    effective_policy = models.ForeignKey(
        JobPolicy,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="jobs",
    )
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
    last_outcome = models.CharField(max_length=16, choices=JobOutcomeKind.choices, blank=True)
    cooldown_until = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Keep the policy captured at enqueue time immutable for this job."""
        if self.pk:
            existing = type(self).objects.filter(pk=self.pk).values("effective_policy_id").first()
            if existing is not None and existing["effective_policy_id"] != self.effective_policy_id:
                raise ValueError("effective job policies are immutable")
        super().save(*args, **kwargs)

    class Meta:
        db_table = "nfx_job"
        indexes = [
            models.Index(fields=("state", "scheduled_at", "-priority"), name="nfx_job_claim_ix"),
            models.Index(fields=("state", "lease_expires_at"), name="nfx_job_expired_lease_ix"),
            models.Index(fields=("logical_target", "created_at"), name="nfx_job_target_ix"),
            models.Index(
                fields=("effective_policy", "state"),
                name="nfx_job_policy_state_ix",
            ),
            models.Index(
                fields=("state", "cooldown_until"),
                name="nfx_job_cooldown_ix",
            ),
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
            models.CheckConstraint(
                condition=(
                    ~Q(state=JobState.BLOCKED)
                    | (
                        Q(lease_owner__isnull=True)
                        & Q(lease_issued_at__isnull=True)
                        & Q(lease_expires_at__isnull=True)
                    )
                ),
                name="nfx_job_blocked_without_lease_ck",
            ),
        ]
