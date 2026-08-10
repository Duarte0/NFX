# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class CollectionScope(models.TextChoices):
    COMPLETE = "completa", "Completa"
    NFE = "nfe", "NF-e"
    NFSE = "nfse", "NFS-e"


class CollectionOrigin(models.TextChoices):
    AUTOMATIC = "automatica", "Automática"
    MANUAL = "manual", "Manual"
    RETRY = "retry", "Retry"


class CollectionExecutionState(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    CONCLUDED = "concluded", "Concluded"
    EMPTY = "empty", "Valid empty"
    PARTIAL = "partial", "Partial"
    RETRYING = "retrying", "Retrying"
    COOLDOWN = "cooldown", "Cooldown"
    BLOCKED = "blocked", "Blocked"
    FAILED = "failed", "Failed"


ACTIVE_COLLECTION_STATES = (
    CollectionExecutionState.QUEUED,
    CollectionExecutionState.RUNNING,
    CollectionExecutionState.RETRYING,
    CollectionExecutionState.COOLDOWN,
    CollectionExecutionState.PARTIAL,
)


class InitialCollectionRequestState(models.TextChoices):
    QUEUED = "queued", "Queued"
    CONSUMED = "consumed", "Consumed"
    BLOCKED = "blocked", "Blocked"


class InitialCollectionRequest(models.Model):
    """The idempotent handoff from a valid certificate to the future collector."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="initial_collection_requests"
    )
    certificate = models.ForeignKey(
        "nfx.Certificate", on_delete=models.PROTECT, related_name="initial_collection_requests"
    )
    kind = models.CharField(max_length=32, default="initial", editable=False)
    state = models.CharField(
        max_length=16,
        choices=InitialCollectionRequestState.choices,
        default=InitialCollectionRequestState.QUEUED,
    )
    idempotency_key = models.CharField(max_length=255, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    safe_error = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "nfx_initial_collection_request"
        constraints = [
            models.UniqueConstraint(
                fields=("company", "kind"), name="nfx_initial_collection_company_kind_uq"
            ),
        ]


class CollectionExecution(models.Model):
    """Durable, safe operational record for one company/family collection."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="collection_executions"
    )
    family = models.CharField(max_length=8)
    requested_scope = models.CharField(max_length=8, choices=CollectionScope.choices)
    origin = models.CharField(max_length=16, choices=CollectionOrigin.choices)
    requester = models.ForeignKey(
        "nfx.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collection_executions",
    )
    retry_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="retries",
    )
    job = models.OneToOneField(
        "nfx.Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="collection_execution",
    )
    effective_policy = models.ForeignKey(
        "nfx.JobPolicy",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="collection_executions",
    )
    state = models.CharField(
        max_length=16,
        choices=CollectionExecutionState.choices,
        default=CollectionExecutionState.QUEUED,
    )
    correlation_id = models.CharField(max_length=128)
    safe_summary = models.JSONField(default=dict)
    safe_error = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_collection_execution"
        indexes = [
            models.Index(
                fields=("company", "family", "created_at"), name="nfx_coll_exec_company_ix"
            ),
            models.Index(fields=("state", "created_at"), name="nfx_coll_exec_state_ix"),
            models.Index(fields=("correlation_id",), name="nfx_coll_exec_corr_ix"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "family"),
                condition=Q(state__in=ACTIVE_COLLECTION_STATES),
                name="nfx_collection_active_company_family_uq",
            ),
            models.CheckConstraint(
                condition=Q(family__in=("nfe", "nfse")),
                name="nfx_collection_family_ck",
            ),
            models.CheckConstraint(
                condition=Q(correlation_id__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_collection_correlation_ck",
            ),
        ]
