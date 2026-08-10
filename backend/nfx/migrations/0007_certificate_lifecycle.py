import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0006_company_lifecycle")]

    operations = [
        migrations.CreateModel(
            name="Certificate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("encrypted_data_key", models.BinaryField()),
                ("data_key_nonce", models.BinaryField()),
                ("encrypted_password", models.BinaryField()),
                ("password_nonce", models.BinaryField()),
                ("fingerprint_sha256", models.CharField(max_length=64)),
                ("certificate_cnpj", models.CharField(max_length=64)),
                ("not_before", models.DateTimeField()),
                ("not_after", models.DateTimeField()),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("current", "Current"),
                            ("replaced", "Replaced"),
                            ("storage_failed", "Storage failed"),
                        ],
                        max_length=20,
                    ),
                ),
                ("key_version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("activated_at", models.DateTimeField(blank=True, null=True)),
                ("replaced_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "artifact",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="certificate",
                        to="nfx.artifact",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="certificates",
                        to="nfx.company",
                    ),
                ),
            ],
            options={
                "db_table": "nfx_certificate",
                "indexes": [
                    models.Index(fields=["company", "state"], name="nfx_cert_company_state_ix"),
                    models.Index(fields=["not_after"], name="nfx_cert_expiry_ix"),
                    models.Index(fields=["state", "created_at"], name="nfx_cert_state_age_ix"),
                ],
            },
        ),
        migrations.CreateModel(
            name="InitialCollectionRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("kind", models.CharField(default="initial", editable=False, max_length=32)),
                (
                    "state",
                    models.CharField(
                        choices=[("queued", "Queued")], default="queued", max_length=16
                    ),
                ),
                ("idempotency_key", models.CharField(editable=False, max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "certificate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="initial_collection_requests",
                        to="nfx.certificate",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="initial_collection_requests",
                        to="nfx.company",
                    ),
                ),
            ],
            options={
                "db_table": "nfx_initial_collection_request",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "kind"), name="nfx_initial_collection_company_kind_uq"
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.UniqueConstraint(
                condition=Q(state="current"),
                fields=("company",),
                name="nfx_certificate_one_current_company_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.UniqueConstraint(
                condition=Q(state="current"),
                fields=("fingerprint_sha256",),
                name="nfx_certificate_current_fingerprint_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                condition=Q(not_after__gt=models.F("not_before")),
                name="nfx_certificate_validity_order_ck",
            ),
        ),
    ]
