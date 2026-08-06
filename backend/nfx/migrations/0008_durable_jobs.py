import uuid

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0007_certificate_lifecycle")]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("job_type", models.CharField(max_length=100)),
                ("logical_target", models.CharField(max_length=255)),
                ("payload", models.JSONField(default=dict)),
                ("priority", models.IntegerField(default=0)),
                ("idempotency_key", models.CharField(max_length=255)),
                ("scheduled_at", models.DateTimeField()),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("state", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed")], default="queued", max_length=16)),
                ("lease_owner", models.CharField(blank=True, max_length=128, null=True)),
                ("lease_issued_at", models.DateTimeField(blank=True, null=True)),
                ("lease_expires_at", models.DateTimeField(blank=True, null=True)),
                ("safe_result", models.JSONField(blank=True, null=True)),
                ("safe_error", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "nfx_job"},
        ),
        migrations.AddConstraint(
            model_name="job",
            constraint=models.UniqueConstraint(
                condition=~Q(state="completed"),
                fields=("idempotency_key",),
                name="nfx_job_active_idempotency_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="job",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(state="running")
                    | (
                        Q(lease_owner__isnull=False)
                        & Q(lease_issued_at__isnull=False)
                        & Q(lease_expires_at__isnull=False)
                    )
                ),
                name="nfx_job_running_lease_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="job",
            constraint=models.CheckConstraint(
                condition=Q(attempt_count__gte=0), name="nfx_job_attempt_nonnegative_ck"
            ),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["state", "scheduled_at", "-priority"], name="nfx_job_claim_ix"),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["state", "lease_expires_at"], name="nfx_job_expired_lease_ix"),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["logical_target", "created_at"], name="nfx_job_target_ix"),
        ),
    ]
