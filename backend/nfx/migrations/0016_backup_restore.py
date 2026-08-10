import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0015_adn_coverage_snapshot")]

    operations = [
        migrations.CreateModel(
            name="BackupSet",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
                        max_length=8,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("complete", "Complete"),
                            ("partial", "Partial"),
                            ("failed", "Failed"),
                            ("expired", "Expired"),
                        ],
                        max_length=16,
                    ),
                ),
                ("version", models.CharField(default="backup-v1", max_length=32)),
                ("idempotency_key", models.CharField(blank=True, max_length=255)),
                ("backup_path", models.CharField(blank=True, max_length=1024)),
                ("manifest", models.JSONField(blank=True, null=True)),
                ("manifest_hash", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("safe_error", models.CharField(blank=True, max_length=64)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "nfx_backup_set"},
        ),
        migrations.CreateModel(
            name="RestoreOperation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("target_reference", models.CharField(max_length=255)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        max_length=16,
                    ),
                ),
                ("validations", models.JSONField(default=dict)),
                ("safe_error", models.CharField(blank=True, max_length=64)),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "backup",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="restore_operations",
                        to="nfx.backupset",
                    ),
                ),
            ],
            options={"db_table": "nfx_restore_operation"},
        ),
        migrations.AddIndex(
            model_name="backupset",
            index=models.Index(fields=("state", "started_at"), name="nfx_backup_state_time_ix"),
        ),
        migrations.AddIndex(
            model_name="backupset",
            index=models.Index(fields=("kind", "started_at"), name="nfx_backup_kind_time_ix"),
        ),
        migrations.AddIndex(
            model_name="restoreoperation",
            index=models.Index(fields=("state", "started_at"), name="nfx_restore_state_time_ix"),
        ),
        migrations.AddIndex(
            model_name="restoreoperation",
            index=models.Index(fields=("backup", "started_at"), name="nfx_restore_backup_time_ix"),
        ),
        migrations.AddConstraint(
            model_name="backupset",
            constraint=models.CheckConstraint(
                condition=Q(size_bytes__gte=0), name="nfx_backup_size_nonnegative_ck"
            ),
        ),
        migrations.AddConstraint(
            model_name="backupset",
            constraint=models.CheckConstraint(
                condition=Q(manifest_hash="") | Q(manifest_hash__regex=r"^[a-f0-9]{64}$"),
                name="nfx_backup_manifest_hash_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="backupset",
            constraint=models.UniqueConstraint(
                condition=~Q(idempotency_key=""),
                fields=("idempotency_key",),
                name="nfx_backup_idempotency_uq",
            ),
        ),
    ]
