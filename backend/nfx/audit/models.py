from __future__ import annotations

import uuid

from django.db import models


class AuditChain(models.Model):
    """The single stream serializes appends without allowing event rewrites."""

    stream = models.CharField(max_length=32, primary_key=True, default="global", editable=False)
    last_sequence = models.BigIntegerField(default=0)
    last_hash = models.CharField(max_length=64, default="0" * 64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nfx_audit_chain"


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.BigIntegerField(unique=True, editable=False)
    occurred_at = models.DateTimeField(editable=False)
    actor_id = models.UUIDField(null=True, blank=True, editable=False)
    actor_role = models.CharField(max_length=16, blank=True, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)
    action = models.CharField(max_length=128, editable=False)
    entity_type = models.CharField(max_length=64, editable=False)
    entity_id = models.CharField(max_length=255, blank=True, editable=False)
    result = models.CharField(max_length=32, editable=False)
    reason = models.CharField(max_length=1000, blank=True, editable=False)
    correlation_id = models.CharField(max_length=128, blank=True, editable=False)
    context = models.JSONField(default=dict, editable=False)
    previous_hash = models.CharField(max_length=64, editable=False)
    event_hash = models.CharField(max_length=64, unique=True, editable=False)

    class Meta:
        db_table = "nfx_audit_event"
        ordering = ("sequence",)
        indexes = [
            models.Index(fields=("occurred_at",), name="nfx_audit_time_ix"),
            models.Index(fields=("actor_id", "occurred_at"), name="nfx_audit_actor_time_ix"),
            models.Index(fields=("action", "occurred_at"), name="nfx_audit_action_time_ix"),
            models.Index(fields=("entity_type", "entity_id"), name="nfx_audit_entity_ix"),
            models.Index(fields=("result", "occurred_at"), name="nfx_audit_result_time_ix"),
        ]
