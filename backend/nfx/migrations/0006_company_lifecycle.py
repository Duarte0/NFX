import uuid

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0005_user_administration_version")]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("cnpj", models.CharField(max_length=64, unique=True)),
                ("legal_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("cadastrada", "Cadastrada"), ("ativa", "Ativa"), ("desativada", "Desativada")], default="cadastrada", max_length=16)),
                ("first_collection_at", models.DateTimeField(blank=True, null=True)),
                ("deactivation_reason", models.CharField(blank=True, max_length=1000, null=True)),
                ("deactivated_at", models.DateTimeField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "nfx_company"},
        ),
        migrations.CreateModel(
            name="CompanyFlow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("family", models.CharField(choices=[("nfe", "NF-e"), ("nfse", "NFS-e")], max_length=8)),
                ("state", models.CharField(choices=[("habilitado", "Habilitado"), ("pausado", "Pausado")], default="habilitado", max_length=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="flows", to="nfx.company")),
            ],
            options={"db_table": "nfx_company_flow"},
        ),
        migrations.CreateModel(
            name="EnrichmentSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(default="opencnpj", max_length=64)),
                ("requested_cnpj", models.CharField(max_length=64)),
                ("obtained_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=[("sucesso", "Sucesso"), ("vazio", "Vazio"), ("nao_encontrado", "Não encontrado"), ("timeout", "Timeout"), ("indisponivel", "Indisponível"), ("malformado", "Conteúdo malformado")], max_length=20)),
                ("public_non_authoritative", models.BooleanField(default=True)),
                ("payload", models.JSONField(default=dict)),
                ("error_code", models.CharField(blank=True, max_length=64)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrichment_snapshots", to="nfx.company")),
            ],
            options={"db_table": "nfx_company_enrichment", "ordering": ("-obtained_at",)},
        ),
        migrations.AddIndex(model_name="company", index=models.Index(fields=["legal_name"], name="nfx_company_name_ix")),
        migrations.AddIndex(model_name="company", index=models.Index(fields=["status"], name="nfx_company_status_ix")),
        migrations.AddIndex(model_name="company", index=models.Index(fields=["cnpj"], name="nfx_company_cnpj_ix")),
        migrations.AddConstraint(model_name="company", constraint=models.CheckConstraint(condition=~Q(status="desativada") | (Q(deactivation_reason__isnull=False) & ~Q(deactivation_reason="")), name="nfx_company_deactivated_reason_ck")),
        migrations.AddIndex(model_name="companyflow", index=models.Index(fields=["family", "state"], name="nfx_company_flow_state_ix")),
        migrations.AddConstraint(model_name="companyflow", constraint=models.UniqueConstraint(fields=("company", "family"), name="nfx_company_flow_uq")),
        migrations.AddIndex(model_name="enrichmentsnapshot", index=models.Index(fields=["company", "obtained_at"], name="nfx_company_enrich_time_ix")),
        migrations.AddIndex(model_name="enrichmentsnapshot", index=models.Index(fields=["source", "status"], name="nfx_company_enrich_status_ix")),
    ]
