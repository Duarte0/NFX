import uuid

from django.db import migrations, models

SQL = """
INSERT INTO nfx_audit_chain (stream, last_sequence, last_hash, updated_at)
VALUES ('global', 0, repeat('0', 64), CURRENT_TIMESTAMP);
CREATE FUNCTION nfx_audit_event_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'nfx audit events are append-only';
END;
$$;
CREATE TRIGGER nfx_audit_event_append_only
BEFORE UPDATE OR DELETE ON nfx_audit_event
FOR EACH ROW EXECUTE FUNCTION nfx_audit_event_immutable();
"""
REVERSE_SQL = """
DROP TRIGGER IF EXISTS nfx_audit_event_append_only ON nfx_audit_event;
DROP FUNCTION IF EXISTS nfx_audit_event_immutable();
DELETE FROM nfx_audit_chain WHERE stream = 'global';
"""


class Migration(migrations.Migration):
    dependencies = [("nfx", "0003_identity")]

    operations = [
        migrations.CreateModel(
            name="AuditChain",
            fields=[
                (
                    "stream",
                    models.CharField(
                        default="global",
                        editable=False,
                        max_length=32,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("last_sequence", models.BigIntegerField(default=0)),
                ("last_hash", models.CharField(default="0" * 64, max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "nfx_audit_chain"},
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("sequence", models.BigIntegerField(editable=False, unique=True)),
                ("occurred_at", models.DateTimeField(editable=False)),
                ("actor_id", models.UUIDField(blank=True, editable=False, null=True)),
                ("actor_role", models.CharField(blank=True, editable=False, max_length=16)),
                ("ip_address", models.GenericIPAddressField(blank=True, editable=False, null=True)),
                ("action", models.CharField(editable=False, max_length=128)),
                ("entity_type", models.CharField(editable=False, max_length=64)),
                ("entity_id", models.CharField(blank=True, editable=False, max_length=255)),
                ("result", models.CharField(editable=False, max_length=32)),
                ("reason", models.CharField(blank=True, editable=False, max_length=1000)),
                ("correlation_id", models.CharField(blank=True, editable=False, max_length=128)),
                ("context", models.JSONField(default=dict, editable=False)),
                ("previous_hash", models.CharField(editable=False, max_length=64)),
                ("event_hash", models.CharField(editable=False, max_length=64, unique=True)),
            ],
            options={"db_table": "nfx_audit_event", "ordering": ("sequence",)},
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["occurred_at"], name="nfx_audit_time_ix"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["actor_id", "occurred_at"], name="nfx_audit_actor_time_ix"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["action", "occurred_at"], name="nfx_audit_action_time_ix"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["entity_type", "entity_id"], name="nfx_audit_entity_ix"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["result", "occurred_at"], name="nfx_audit_result_time_ix"),
        ),
        migrations.RunSQL(SQL, REVERSE_SQL),
    ]
