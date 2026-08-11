import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q

# Generated migration declarations are kept aligned with Django's serializer.
# ruff: noqa: E501


class Migration(migrations.Migration):
    dependencies = [("nfx", "0018_export_exportitem_export_nfx_export_owner_time_ix_and_more")]

    operations = [
        migrations.CreateModel(
            name="DocumentRender",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "pdf_type",
                    models.CharField(
                        choices=[("danfe", "DANFE"), ("danfse", "DANFSe")], max_length=16
                    ),
                ),
                (
                    "representation",
                    models.CharField(
                        choices=[("danfe", "DANFE"), ("danfse", "DANFSe")], max_length=16
                    ),
                ),
                ("renderer_id", models.CharField(max_length=64)),
                ("renderer_version", models.CharField(max_length=32)),
                ("source_digest", models.CharField(max_length=64)),
                ("digest", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("mime_type", models.CharField(default="application/pdf", max_length=255)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("finalized", "Finalized"),
                            ("failed", "Failed"),
                            ("unsupported", "Unsupported"),
                            ("missing", "Missing"),
                            ("divergent", "Divergent"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("safe_error", models.CharField(blank=True, max_length=64)),
                ("safe_result", models.JSONField(default=dict)),
                ("correlation_id", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                (
                    "artifact",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_renders",
                        to="nfx.artifact",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="renders",
                        to="nfx.document",
                    ),
                ),
                (
                    "job",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_render",
                        to="nfx.job",
                    ),
                ),
                (
                    "source_artifact",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_renders_source",
                        to="nfx.artifact",
                    ),
                ),
            ],
            options={"db_table": "nfx_document_render"},
        ),
        migrations.AddIndex(
            model_name="documentrender",
            index=models.Index(fields=["document", "state"], name="nfx_doc_render_state_ix"),
        ),
        migrations.AddIndex(
            model_name="documentrender",
            index=models.Index(
                fields=["renderer_id", "renderer_version"], name="nfx_doc_render_version_ix"
            ),
        ),
        migrations.AddConstraint(
            model_name="documentrender",
            constraint=models.UniqueConstraint(
                fields=[
                    "document",
                    "pdf_type",
                    "representation",
                    "renderer_id",
                    "renderer_version",
                ],
                name="nfx_doc_render_identity_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="documentrender",
            constraint=models.CheckConstraint(
                condition=Q(size_bytes__isnull=True) | Q(size_bytes__gte=0),
                name="nfx_doc_render_size_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="documentrender",
            constraint=models.CheckConstraint(
                condition=Q(mime_type="application/pdf"), name="nfx_doc_render_mime_ck"
            ),
        ),
    ]
