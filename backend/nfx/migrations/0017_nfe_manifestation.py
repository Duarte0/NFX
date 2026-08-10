import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0016_backup_restore")]

    operations = [
        migrations.CreateModel(
            name="NFeManifestation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("target_document_id", models.UUIDField()),
                ("flow", models.CharField(max_length=16)),
                ("manifestation_type", models.CharField(max_length=32)),
                ("source", models.CharField(max_length=64)),
                ("policy_reference", models.CharField(max_length=128)),
                ("certificate_reference", models.CharField(max_length=128)),
                ("correlation_id", models.CharField(max_length=128)),
                ("idempotency_reference", models.CharField(max_length=128)),
                ("idempotency_key", models.CharField(editable=False, max_length=255, unique=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("accepted", "Accepted"),
                            ("denied", "Denied"),
                            ("retry", "Retry"),
                            ("cooldown", "Cooldown"),
                            ("blocked", "Blocked"),
                            ("quarantined", "Quarantined"),
                            ("conflict", "Conflict"),
                        ],
                        max_length=16,
                    ),
                ),
                ("outcome", models.CharField(blank=True, max_length=32)),
                ("result_code", models.CharField(blank=True, max_length=64)),
                ("safe_result", models.JSONField(default=dict)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nfe_manifestations",
                        to="nfx.company",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nfe_manifestations",
                        to="nfx.document",
                    ),
                ),
                (
                    "job",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nfe_manifestation",
                        to="nfx.job",
                    ),
                ),
            ],
            options={"db_table": "nfx_nfe_manifestation"},
        ),
        migrations.AddIndex(
            model_name="nfemanifestation",
            index=models.Index(
                fields=("company", "flow", "state"), name="nfx_nfe_manifest_state_ix"
            ),
        ),
        migrations.AddIndex(
            model_name="nfemanifestation",
            index=models.Index(
                fields=("target_document_id", "flow"), name="nfx_nfe_manifest_target_ix"
            ),
        ),
        migrations.AddIndex(
            model_name="nfemanifestation",
            index=models.Index(fields=("correlation_id",), name="nfx_nfe_manifest_corr_ix"),
        ),
        migrations.AddConstraint(
            model_name="nfemanifestation",
            constraint=models.CheckConstraint(
                condition=Q(flow__in=("received", "issued")), name="nfx_nfe_manifest_flow_ck"
            ),
        ),
        migrations.AddConstraint(
            model_name="nfemanifestation",
            constraint=models.CheckConstraint(
                condition=Q(manifestation_type="science_of_operation"),
                name="nfx_nfe_manifest_type_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="nfemanifestation",
            constraint=models.CheckConstraint(
                condition=Q(source__regex=r"^[A-Za-z0-9_.:/-]{1,64}$"),
                name="nfx_nfe_manifest_source_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="nfemanifestation",
            constraint=models.CheckConstraint(
                condition=Q(idempotency_reference__regex=r"^[A-Za-z0-9_.:/-]{1,128}$"),
                name="nfx_nfe_manifest_idempotency_ref_ck",
            ),
        ),
    ]
