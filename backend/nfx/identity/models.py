# mypy: disable-error-code=var-annotated
from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q


class Role(models.TextChoices):
    ADMINISTRATOR = "administrador", "Administrador"
    OPERATOR = "operador", "Operador"
    VIEWER = "visualizador", "Visualizador"


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=16, choices=Role.choices)
    password_hash = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    revocation_version = models.PositiveIntegerField(default=1)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("active", "role"), name="nfx_user_active_role_ix")]


class IdentitySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    revocation_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("user", "expires_at"), name="nfx_session_user_exp_ix"),
            models.Index(fields=("expires_at",), name="nfx_session_exp_ix"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gte=models.F("created_at")),
                name="nfx_session_expiry_after_create_ck",
            )
        ]


class LoginThrottle(models.Model):
    """A keyed subject digest avoids retaining an account identifier on failed logins."""

    subject_hash = models.CharField(max_length=64, primary_key=True)
    failures = models.PositiveIntegerField(default=0)
    next_allowed_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
