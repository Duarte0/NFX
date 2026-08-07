import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0008_durable_jobs")]

    operations = [
        migrations.CreateModel(
            name="JobPolicy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("source_scope", models.CharField(max_length=100)),
                ("flow_scope", models.CharField(max_length=100)),
                ("version", models.PositiveIntegerField()),
                ("valid_from", models.DateTimeField()),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("retry_limit", models.PositiveIntegerField(default=3)),
                ("backoff_initial_seconds", models.PositiveIntegerField(default=1)),
                ("backoff_cap_seconds", models.PositiveIntegerField(default=3600)),
                ("jitter_seconds", models.PositiveIntegerField(default=0)),
                ("cooldown_seconds", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "nfx_job_policy",
                "indexes": [
                    models.Index(
                        fields=["source_scope", "flow_scope", "valid_from"],
                        name="nfx_policy_scope_valid_ix",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="jobpolicy",
            constraint=models.UniqueConstraint(
                fields=("source_scope", "flow_scope", "version"),
                name="nfx_policy_scope_version_uq",
            ),
        ),
        migrations.AddConstraint(
            model_name="jobpolicy",
            constraint=models.CheckConstraint(
                condition=Q(valid_until__isnull=True) | Q(valid_until__gt=models.F("valid_from")),
                name="nfx_policy_validity_order_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="jobpolicy",
            constraint=models.CheckConstraint(
                condition=Q(backoff_cap_seconds__gte=models.F("backoff_initial_seconds")),
                name="nfx_policy_backoff_cap_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="jobpolicy",
            constraint=models.CheckConstraint(
                condition=(
                    Q(retry_limit__gte=0)
                    & Q(backoff_initial_seconds__gt=0)
                    & Q(backoff_cap_seconds__gt=0)
                    & Q(jitter_seconds__gte=0)
                    & Q(cooldown_seconds__gte=0)
                ),
                name="nfx_policy_timing_values_ck",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="effective_policy",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="jobs",
                to="nfx.jobpolicy",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="last_outcome",
            field=models.CharField(
                blank=True,
                choices=[
                    ("success", "Success"),
                    ("temporary", "Temporary"),
                    ("cooldown", "Cooldown"),
                    ("permanent", "Permanent"),
                    ("partial", "Partial"),
                ],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="cooldown_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="blocked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="job",
            name="blocked_reason",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="job",
            name="state",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("completed", "Completed"),
                    ("blocked", "Blocked"),
                ],
                default="queued",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="job",
            constraint=models.CheckConstraint(
                condition=(
                    ~Q(state="blocked")
                    | (
                        Q(lease_owner__isnull=True)
                        & Q(lease_issued_at__isnull=True)
                        & Q(lease_expires_at__isnull=True)
                    )
                ),
                name="nfx_job_blocked_without_lease_ck",
            ),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(
                fields=["effective_policy", "state"], name="nfx_job_policy_state_ix"
            ),
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["state", "cooldown_until"], name="nfx_job_cooldown_ix"),
        ),
    ]
