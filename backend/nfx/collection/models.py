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


class IngestionPageState(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETE = "complete", "Complete"
    EMPTY = "empty", "Valid empty"
    PARTIAL = "partial", "Partial"
    FAILED = "failed", "Failed"


class ReceivedUnitState(models.TextChoices):
    PENDING = "pending", "Pending"
    PERSISTED = "persisted", "Persisted"
    REPLAY = "replay", "Replay"
    QUARANTINE = "quarantine", "Quarantine"
    CONFLICT = "conflict", "Conflict"
    FAILED = "failed", "Failed"


INGESTION_TERMINAL_UNIT_STATES = (
    ReceivedUnitState.PERSISTED,
    ReceivedUnitState.REPLAY,
    ReceivedUnitState.QUARANTINE,
    ReceivedUnitState.CONFLICT,
)


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


class IngestionCheckpoint(models.Model):
    """The sole durable continuation position for one collection scope."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="ingestion_checkpoints"
    )
    family = models.CharField(max_length=8)
    flow = models.CharField(max_length=64)
    cursor = models.CharField(max_length=128, blank=True)
    nsu = models.CharField(max_length=128, blank=True)
    last_page = models.ForeignKey(
        "nfx.IngestionPage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="checkpoint_completions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_ingestion_checkpoint"
        constraints = [
            models.UniqueConstraint(
                fields=("company", "family", "flow"), name="nfx_ingest_checkpoint_scope_uq"
            ),
            models.CheckConstraint(
                condition=Q(family__in=("nfe", "adn", "nfse")),
                name="nfx_ingest_checkpoint_family_ck",
            ),
            models.CheckConstraint(
                condition=Q(cursor="") | Q(nsu=""), name="nfx_ingest_checkpoint_position_ck"
            ),
            models.CheckConstraint(
                condition=Q(flow__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"),
                name="nfx_ingest_checkpoint_flow_ck",
            ),
        ]
        indexes = [
            models.Index(fields=("company", "family", "updated_at"), name="nfx_ingest_cp_age_ix"),
        ]


class IngestionPage(models.Model):
    """One adapter response, including an explicit incomplete outcome."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="ingestion_pages"
    )
    execution = models.ForeignKey(
        "nfx.CollectionExecution",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ingestion_pages",
    )
    family = models.CharField(max_length=8)
    flow = models.CharField(max_length=64)
    page_key = models.CharField(max_length=160)
    request_cursor = models.CharField(max_length=128, blank=True)
    request_nsu = models.CharField(max_length=128, blank=True)
    next_cursor = models.CharField(max_length=128, blank=True)
    next_nsu = models.CharField(max_length=128, blank=True)
    adapter_outcome = models.CharField(max_length=32)
    coverage = models.CharField(max_length=16)
    state = models.CharField(max_length=16, choices=IngestionPageState.choices)
    safe_error = models.CharField(max_length=64, blank=True)
    unit_count = models.PositiveIntegerField(default=0)
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_ingestion_page"
        constraints = [
            models.UniqueConstraint(
                fields=("company", "family", "flow", "page_key"),
                name="nfx_ingest_page_scope_key_uq",
            ),
            models.CheckConstraint(
                condition=Q(family__in=("nfe", "adn", "nfse")), name="nfx_ingest_page_family_ck"
            ),
            models.CheckConstraint(
                condition=Q(request_cursor="") | Q(request_nsu=""),
                name="nfx_ingest_page_request_position_ck",
            ),
            models.CheckConstraint(
                condition=Q(next_cursor="") | Q(next_nsu=""),
                name="nfx_ingest_page_next_position_ck",
            ),
            models.CheckConstraint(
                condition=Q(flow__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"), name="nfx_ingest_page_flow_ck"
            ),
        ]
        indexes = [
            models.Index(
                fields=("company", "family", "flow", "state"), name="nfx_ingest_page_state_ix"
            ),
            models.Index(fields=("state", "created_at"), name="nfx_ingest_page_age_ix"),
        ]


class ReceivedUnit(models.Model):
    """A bounded unit reference whose terminal treatment is retryable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(IngestionPage, on_delete=models.PROTECT, related_name="units")
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="received_units"
    )
    family = models.CharField(max_length=8)
    flow = models.CharField(max_length=64)
    identity = models.CharField(max_length=128)
    kind = models.CharField(max_length=16)
    parent_identity = models.CharField(max_length=128, blank=True)
    content_hash = models.CharField(max_length=64)
    artifact = models.ForeignKey(
        "nfx.Artifact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_units",
    )
    document = models.ForeignKey(
        "nfx.Document",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_units",
    )
    event = models.ForeignKey(
        "nfx.DocumentEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_units",
    )
    state = models.CharField(max_length=16, choices=ReceivedUnitState.choices)
    safe_reason = models.CharField(max_length=64, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    terminal_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_received_unit"
        constraints = [
            models.UniqueConstraint(
                fields=("page", "identity"), name="nfx_received_unit_page_identity_uq"
            ),
            models.CheckConstraint(
                condition=Q(family__in=("nfe", "adn", "nfse")), name="nfx_received_unit_family_ck"
            ),
            models.CheckConstraint(
                condition=Q(content_hash__regex=r"^[0-9a-f]{64}$"), name="nfx_received_unit_hash_ck"
            ),
            models.CheckConstraint(
                condition=Q(flow__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"),
                name="nfx_received_unit_flow_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=("company", "family", "flow", "identity"),
                name="nfx_received_unit_lookup_ix",
            ),
            models.Index(fields=("state", "last_attempt_at"), name="nfx_received_unit_retry_ix"),
            models.Index(fields=("content_hash",), name="nfx_received_unit_hash_ix"),
        ]
