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


class DocumentRelationship(models.TextChoices):
    EVENT = "event", "Event"
    SUBSTITUTION = "substitution", "Substitution"


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
