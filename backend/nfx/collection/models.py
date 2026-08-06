# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models


class InitialCollectionRequestState(models.TextChoices):
    QUEUED = "queued", "Queued"


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

    class Meta:
        db_table = "nfx_initial_collection_request"
        constraints = [
            models.UniqueConstraint(
                fields=("company", "kind"), name="nfx_initial_collection_company_kind_uq"
            ),
        ]
