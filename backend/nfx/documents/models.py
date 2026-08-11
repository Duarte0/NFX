from __future__ import annotations

import uuid

from django.db import models

from nfx.artifacts.models import Artifact
from nfx.companies.models import Company


class DocumentFamily(models.TextChoices):
    NFE = "nfe", "NF-e"
    NFSE = "nfse", "NFS-e"


class DocumentState(models.TextChoices):
    PERSISTED = "persisted", "Persisted"
    CONFLICT = "conflict", "Conflict"


class DocumentSituation(models.TextChoices):
    AUTHORIZED = "authorized", "Authorized"
    CANCELLED = "cancelled", "Cancelled"
    UNKNOWN = "unknown", "Unknown"


class PdfRepresentation(models.TextChoices):
    DANFE = "danfe", "DANFE"
    DANFSE = "danfse", "DANFSe"

    @classmethod
    def for_family(cls, family: str) -> PdfRepresentation:
        if family == DocumentFamily.NFE:
            return cls.DANFE
        if family == DocumentFamily.NFSE:
            return cls.DANFSE
        raise ValueError("document family is unsupported")


class DocumentRenderState(models.TextChoices):
    PENDING = "pending", "Pending"
    FINALIZED = "finalized", "Finalized"
    FAILED = "failed", "Failed"
    UNSUPPORTED = "unsupported", "Unsupported"
    MISSING = "missing", "Missing"
    DIVERGENT = "divergent", "Divergent"


class DocumentRelationship(models.TextChoices):
    EVENT = "event", "Event"
    SUBSTITUTION = "substitution", "Substitution"


class NFeManifestationState(models.TextChoices):
    QUEUED = "queued", "Queued"
    ACCEPTED = "accepted", "Accepted"
    DENIED = "denied", "Denied"
    RETRY = "retry", "Retry"
    COOLDOWN = "cooldown", "Cooldown"
    BLOCKED = "blocked", "Blocked"
    QUARANTINED = "quarantined", "Quarantined"
    CONFLICT = "conflict", "Conflict"


class Document(models.Model):
    """Fiscal identity and metadata; payload bytes remain owned by artifacts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="documents")
    family = models.CharField(max_length=8, choices=DocumentFamily.choices)
    role = models.CharField(max_length=16)
    category = models.CharField(max_length=32)
    source = models.CharField(max_length=64)
    flow = models.CharField(max_length=64)
    identity_kind = models.CharField(max_length=32)
    normalized_identity = models.CharField(max_length=255)
    identity_key = models.CharField(max_length=1024, unique=True, editable=False)
    emitted_at = models.DateTimeField()
    authorized_at = models.DateTimeField(null=True, blank=True)
    competence = models.DateField()
    situation = models.CharField(max_length=16, choices=DocumentSituation.choices)
    state = models.CharField(
        max_length=16, choices=DocumentState.choices, default=DocumentState.PERSISTED
    )
    origin_execution_ref = models.CharField(max_length=128)
    correlation_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_document"
        indexes = [
            models.Index(fields=("company", "competence"), name="nfx_document_company_comp_ix"),
            models.Index(fields=("family", "emitted_at"), name="nfx_document_family_emit_ix"),
            models.Index(fields=("normalized_identity",), name="nfx_document_identity_ix"),
            models.Index(fields=("situation", "state"), name="nfx_document_situation_ix"),
            models.Index(fields=("source", "flow", "category"), name="nfx_document_context_ix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(emitted_at__isnull=False),
                name="nfx_document_emitted_required_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(origin_execution_ref__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_document_origin_ref_ck",
            ),
        ]


class DocumentEvidence(models.Model):
    """Immutable references to original artifacts, including conflicting evidence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="evidence")
    artifact = models.ForeignKey(
        Artifact, on_delete=models.PROTECT, related_name="document_evidence"
    )
    digest = models.CharField(max_length=64)
    size_bytes = models.BigIntegerField()
    conflicting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nfx_document_evidence"
        constraints = [
            models.UniqueConstraint(
                fields=("document", "artifact"), name="nfx_document_evidence_artifact_uq"
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__gte=0), name="nfx_document_evidence_size_ck"
            ),
        ]
        indexes = [
            models.Index(fields=("document", "digest"), name="nfx_doc_evidence_digest_ix"),
        ]


class DocumentRender(models.Model):
    """Versioned derived PDF metadata; source evidence remains immutable."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="renders")
    source_artifact = models.ForeignKey(
        Artifact, on_delete=models.PROTECT, related_name="document_renders_source"
    )
    artifact = models.ForeignKey(
        Artifact,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_renders",
    )
    pdf_type = models.CharField(max_length=16, choices=PdfRepresentation.choices)
    representation = models.CharField(max_length=16, choices=PdfRepresentation.choices)
    renderer_id = models.CharField(max_length=64)
    renderer_version = models.CharField(max_length=32)
    source_digest = models.CharField(max_length=64)
    digest = models.CharField(max_length=64, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=255, default="application/pdf")
    state = models.CharField(
        max_length=16, choices=DocumentRenderState.choices, default=DocumentRenderState.PENDING
    )
    safe_error = models.CharField(max_length=64, blank=True)
    safe_result = models.JSONField(default=dict)
    correlation_id = models.CharField(max_length=128, blank=True)
    job = models.OneToOneField(
        "nfx.Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_render",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "nfx_document_render"
        indexes = [
            models.Index(fields=("document", "state"), name="nfx_doc_render_state_ix"),
            models.Index(
                fields=("renderer_id", "renderer_version"), name="nfx_doc_render_version_ix"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "document",
                    "pdf_type",
                    "representation",
                    "renderer_id",
                    "renderer_version",
                ),
                name="nfx_doc_render_identity_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__isnull=True) | models.Q(size_bytes__gte=0),
                name="nfx_doc_render_size_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(mime_type="application/pdf"),
                name="nfx_doc_render_mime_ck",
            ),
        ]


class DocumentEvent(models.Model):
    """An event or substitution attached to a compatible parent document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="events")
    family = models.CharField(max_length=8, choices=DocumentFamily.choices)
    role = models.CharField(max_length=16, default="evento")
    category = models.CharField(max_length=32)
    source = models.CharField(max_length=64)
    flow = models.CharField(max_length=64)
    identity_kind = models.CharField(max_length=32)
    normalized_identity = models.CharField(max_length=255)
    identity_key = models.CharField(max_length=1024, unique=True, editable=False)
    occurred_at = models.DateTimeField()
    situation = models.CharField(max_length=16, choices=DocumentSituation.choices)
    relationship_type = models.CharField(max_length=16, choices=DocumentRelationship.choices)
    state = models.CharField(
        max_length=16, choices=DocumentState.choices, default=DocumentState.PERSISTED
    )
    origin_execution_ref = models.CharField(max_length=128)
    correlation_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nfx_document_event"
        indexes = [
            models.Index(
                fields=("parent_document", "occurred_at"), name="nfx_event_parent_time_ix"
            ),
            models.Index(fields=("family", "relationship_type"), name="nfx_event_family_rel_ix"),
            models.Index(fields=("normalized_identity",), name="nfx_event_identity_ix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(origin_execution_ref__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_event_origin_ref_ck",
            ),
        ]


class DocumentEventEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(DocumentEvent, on_delete=models.PROTECT, related_name="evidence")
    artifact = models.ForeignKey(
        Artifact, on_delete=models.PROTECT, related_name="document_event_evidence"
    )
    digest = models.CharField(max_length=64)
    size_bytes = models.BigIntegerField()
    conflicting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "nfx_document_event_evidence"
        constraints = [
            models.UniqueConstraint(
                fields=("event", "artifact"), name="nfx_event_evidence_artifact_uq"
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__gte=0), name="nfx_event_evidence_size_ck"
            ),
        ]
        indexes = [
            models.Index(fields=("event", "digest"), name="nfx_evt_evidence_digest_ix"),
        ]


class NFeManifestation(models.Model):
    """Durable safe result for one simulator-backed NF-e manifestation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="nfe_manifestations"
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nfe_manifestations",
    )
    target_document_id = models.UUIDField()
    flow = models.CharField(max_length=16)
    manifestation_type = models.CharField(max_length=32)
    source = models.CharField(max_length=64)
    policy_reference = models.CharField(max_length=128)
    certificate_reference = models.CharField(max_length=128)
    correlation_id = models.CharField(max_length=128)
    idempotency_reference = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=255, unique=True, editable=False)
    state = models.CharField(max_length=16, choices=NFeManifestationState.choices)
    outcome = models.CharField(max_length=32, blank=True)
    result_code = models.CharField(max_length=64, blank=True)
    safe_result = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(null=True, blank=True)
    job = models.OneToOneField(
        "nfx.Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nfe_manifestation",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_nfe_manifestation"
        indexes = [
            models.Index(fields=("company", "flow", "state"), name="nfx_nfe_manifest_state_ix"),
            models.Index(fields=("target_document_id", "flow"), name="nfx_nfe_manifest_target_ix"),
            models.Index(fields=("correlation_id",), name="nfx_nfe_manifest_corr_ix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(flow__in=("received", "issued")),
                name="nfx_nfe_manifest_flow_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(manifestation_type="science_of_operation"),
                name="nfx_nfe_manifest_type_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(source__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"),
                name="nfx_nfe_manifest_source_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(idempotency_reference__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_nfe_manifest_idempotency_ref_ck",
            ),
        ]
