# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class CertificateState(models.TextChoices):
    PENDING = "pending", "Pending"
    CURRENT = "current", "Current"
    REPLACED = "replaced", "Replaced"
    STORAGE_FAILED = "storage_failed", "Storage failed"


class Certificate(models.Model):
    """Certificate metadata plus ciphertext references; plaintext never persists."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "nfx.Company", on_delete=models.PROTECT, related_name="certificates"
    )
    artifact = models.OneToOneField(
        "nfx.Artifact",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificate",
    )
    encrypted_data_key = models.BinaryField()
    data_key_nonce = models.BinaryField()
    encrypted_password = models.BinaryField()
    password_nonce = models.BinaryField()
    fingerprint_sha256 = models.CharField(max_length=64)
    certificate_cnpj = models.CharField(max_length=64)
    not_before = models.DateTimeField()
    not_after = models.DateTimeField()
    state = models.CharField(max_length=20, choices=CertificateState.choices)
    key_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    replaced_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_certificate"
        constraints = [
            models.UniqueConstraint(
                fields=("company",),
                condition=Q(state=CertificateState.CURRENT),
                name="nfx_certificate_one_current_company_uq",
            ),
            models.UniqueConstraint(
                fields=("fingerprint_sha256",),
                condition=Q(state=CertificateState.CURRENT),
                name="nfx_certificate_current_fingerprint_uq",
            ),
            models.CheckConstraint(
                condition=Q(not_after__gt=models.F("not_before")),
                name="nfx_certificate_validity_order_ck",
            ),
        ]
        indexes = [
            models.Index(fields=("company", "state"), name="nfx_cert_company_state_ix"),
            models.Index(fields=("not_after",), name="nfx_cert_expiry_ix"),
            models.Index(fields=("state", "created_at"), name="nfx_cert_state_age_ix"),
        ]
