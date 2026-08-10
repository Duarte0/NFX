# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class CompanyStatus(models.TextChoices):
    REGISTERED = "cadastrada", "Cadastrada"
    ACTIVE = "ativa", "Ativa"
    DEACTIVATED = "desativada", "Desativada"


class FlowFamily(models.TextChoices):
    NFE = "nfe", "NF-e"
    NFSE = "nfse", "NFS-e"


class FlowState(models.TextChoices):
    ENABLED = "habilitado", "Habilitado"
    PAUSED = "pausado", "Pausado"


class AdnCoverageStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    NONE = "none", "No coverage"
    UNKNOWN = "unknown", "Unknown"


class EnrichmentStatus(models.TextChoices):
    SUCCESS = "sucesso", "Sucesso"
    EMPTY = "vazio", "Vazio"
    NOT_FOUND = "nao_encontrado", "Não encontrado"
    TIMEOUT = "timeout", "Timeout"
    UNAVAILABLE = "indisponivel", "Indisponível"
    MALFORMED = "malformado", "Conteúdo malformado"


class Company(models.Model):
    """The owner of company identity, lifecycle, flows, and public enrichment."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The current validator accepts numeric CNPJs, while the physical shape is
    # intentionally wider so a future alphanumeric CNPJ does not require a rewrite.
    cnpj = models.CharField(max_length=64, unique=True)
    legal_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=CompanyStatus.choices, default=CompanyStatus.REGISTERED
    )
    first_collection_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=1000, null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_company"
        indexes = [
            models.Index(fields=("legal_name",), name="nfx_company_name_ix"),
            models.Index(fields=("status",), name="nfx_company_status_ix"),
            models.Index(fields=("cnpj",), name="nfx_company_cnpj_ix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(status=CompanyStatus.DEACTIVATED)
                    | (Q(deactivation_reason__isnull=False) & ~Q(deactivation_reason=""))
                ),
                name="nfx_company_deactivated_reason_ck",
            )
        ]


class CompanyFlow(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="flows")
    family = models.CharField(max_length=8, choices=FlowFamily.choices)
    state = models.CharField(max_length=10, choices=FlowState.choices, default=FlowState.ENABLED)
    collection_state = models.CharField(max_length=16, default="idle")
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    next_scheduled_at = models.DateTimeField(null=True, blank=True)
    cooldown_until = models.DateTimeField(null=True, blank=True)
    blocked_reason = models.CharField(max_length=64, blank=True)
    safe_error = models.CharField(max_length=64, blank=True)
    progress_current = models.PositiveIntegerField(default=0)
    progress_total = models.PositiveIntegerField(default=0)
    active_execution = models.ForeignKey(
        "nfx.CollectionExecution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_flow_rows",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_company_flow"
        constraints = [
            models.UniqueConstraint(fields=("company", "family"), name="nfx_company_flow_uq"),
        ]
        indexes = [
            models.Index(fields=("family", "state"), name="nfx_company_flow_state_ix"),
            models.Index(
                fields=("collection_state", "next_scheduled_at"), name="nfx_flow_collection_due_ix"
            ),
        ]


class AdnCoverageSnapshot(models.Model):
    """Versioned, safe evidence that one company was checked by the ADN boundary."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="adn_coverage_snapshots"
    )
    source = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=AdnCoverageStatus.choices)
    verified_at = models.DateTimeField()
    evidence_reference = models.CharField(max_length=128, blank=True)
    policy_version = models.CharField(max_length=128)

    class Meta:
        db_table = "nfx_adn_coverage_snapshot"
        ordering = ("-verified_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(source__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"),
                name="nfx_adn_coverage_source_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(policy_version__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_adn_coverage_policy_ck",
            ),
            models.CheckConstraint(
                condition=models.Q(evidence_reference="")
                | models.Q(evidence_reference__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_adn_coverage_evidence_ck",
            ),
        ]
        indexes = [
            models.Index(fields=("company", "status"), name="nfx_adn_coverage_status_ix"),
            models.Index(fields=("company", "verified_at"), name="nfx_adn_coverage_time_ix"),
        ]


class EnrichmentSnapshot(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="enrichment_snapshots"
    )
    source = models.CharField(max_length=64, default="opencnpj")
    requested_cnpj = models.CharField(max_length=64)
    obtained_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=EnrichmentStatus.choices)
    public_non_authoritative = models.BooleanField(default=True)
    payload = models.JSONField(default=dict)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "nfx_company_enrichment"
        ordering = ("-obtained_at",)
        indexes = [
            models.Index(fields=("company", "obtained_at"), name="nfx_company_enrich_time_ix"),
            models.Index(fields=("source", "status"), name="nfx_company_enrich_status_ix"),
        ]
