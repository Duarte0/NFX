import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0017_nfe_manifestation")]

    operations = [
        migrations.CreateModel(
            name="Export",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("filter_snapshot", models.JSONField(default=dict)),
                ("selection_snapshot", models.JSONField(default=dict)),
                ("expected_count", models.PositiveIntegerField(default=0)),
                ("produced_count", models.PositiveIntegerField(default=0)),
                ("expected_bytes", models.BigIntegerField(default=0)),
                ("produced_bytes", models.BigIntegerField(default=0)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("complete", "Complete"),
                            ("partial", "Partial"),
                            ("failed", "Failed"),
                            ("available", "Available"),
                            ("expired", "Expired"),
                            ("excluded", "Excluded"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("safe_result", models.JSONField(default=dict)),
                ("safe_error", models.CharField(blank=True, max_length=64)),
                ("idempotency_key", models.CharField(max_length=64)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "job",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="export",
                        to="nfx.job",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="exports",
                        to="nfx.user",
                    ),
                ),
                (
                    "zip_artifact",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="zip_export",
                        to="nfx.artifact",
                    ),
                ),
            ],
            options={"db_table": "nfx_export"},
        ),
        migrations.CreateModel(
            name="ExportItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("digest", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("content_type", models.CharField(blank=True, max_length=255)),
                ("sequence", models.PositiveIntegerField()),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("included", "Included"),
                            ("missing", "Missing"),
                            ("divergent", "Divergent"),
                            ("failed", "Failed"),
                            ("excluded", "Excluded"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("archive_path", models.CharField(blank=True, max_length=255)),
                ("safe_error", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "artifact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="export_items",
                        to="nfx.artifact",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="export_items",
                        to="nfx.document",
                    ),
                ),
                (
                    "export",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="nfx.export",
                    ),
                ),
            ],
            options={"db_table": "nfx_export_item", "ordering": ("sequence", "id")},
        ),
        migrations.AddIndex(
            model_name="export",
            index=models.Index(
                fields=["requester", "created_at"], name="nfx_export_owner_time_ix"
            ),
        ),
        migrations.AddIndex(
            model_name="export",
            index=models.Index(fields=["state", "expires_at"], name="nfx_export_expiry_ix"),
        ),
        migrations.AddConstraint(
            model_name="export",
            constraint=models.UniqueConstraint(
                fields=("requester", "idempotency_key"), name="nfx_export_owner_key_uq"
            ),
        ),
        migrations.AddConstraint(
            model_name="export",
            constraint=models.CheckConstraint(
                condition=Q(expected_count__gte=0), name="nfx_export_expected_count_ck"
            ),
        ),
        migrations.AddConstraint(
            model_name="export",
            constraint=models.CheckConstraint(
                condition=Q(produced_count__gte=0), name="nfx_export_produced_count_ck"
            ),
        ),
        migrations.AddConstraint(
            model_name="export",
            constraint=models.CheckConstraint(
                condition=Q(expected_bytes__gte=0), name="nfx_export_expected_bytes_ck"
            ),
        ),
        migrations.AddConstraint(
            model_name="export",
            constraint=models.CheckConstraint(
                condition=Q(produced_bytes__gte=0), name="nfx_export_produced_bytes_ck"
            ),
        ),
        migrations.AddIndex(
            model_name="exportitem",
            index=models.Index(
                fields=["export", "state"], name="nfx_export_item_state_ix"
            ),
        ),
        migrations.AddConstraint(
            model_name="exportitem",
            constraint=models.UniqueConstraint(
                fields=("export", "document"), name="nfx_export_document_uq"
            ),
        ),
        migrations.AddConstraint(
            model_name="exportitem",
            constraint=models.UniqueConstraint(
                fields=("export", "sequence"), name="nfx_export_sequence_uq"
            ),
        ),
        migrations.AddConstraint(
            model_name="exportitem",
            constraint=models.CheckConstraint(
                condition=Q(size_bytes__gte=0), name="nfx_export_item_size_ck"
            ),
        ),
    ]
