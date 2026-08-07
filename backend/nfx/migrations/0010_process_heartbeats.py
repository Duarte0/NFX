import uuid

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("nfx", "0009_job_policies")]

    operations = [
        migrations.CreateModel(
            name="ProcessHeartbeat",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("component", models.CharField(max_length=16)),
                ("process_id", models.CharField(max_length=128)),
                ("started_at", models.DateTimeField()),
                ("last_seen_at", models.DateTimeField()),
                ("status", models.CharField(default="running", max_length=16)),
            ],
            options={
                "db_table": "nfx_process_heartbeat",
                "indexes": [
                    models.Index(
                        fields=["component", "-last_seen_at"],
                        name="nfx_heartbeat_component_ix",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="processheartbeat",
            constraint=models.UniqueConstraint(
                fields=("component", "process_id"), name="nfx_heartbeat_identity_uq"
            ),
        ),
        migrations.AddConstraint(
            model_name="processheartbeat",
            constraint=models.CheckConstraint(
                condition=Q(component__in=("worker", "scheduler")),
                name="nfx_heartbeat_component_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="processheartbeat",
            constraint=models.CheckConstraint(
                condition=Q(status__in=("running", "stopping")),
                name="nfx_heartbeat_status_ck",
            ),
        ),
        migrations.AddConstraint(
            model_name="processheartbeat",
            constraint=models.CheckConstraint(
                condition=Q(process_id__regex=r"^[a-z][a-z0-9_.-]{0,127}$"),
                name="nfx_heartbeat_process_id_ck",
            ),
        ),
    ]
