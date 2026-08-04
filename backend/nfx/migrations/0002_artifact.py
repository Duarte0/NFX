from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [("nfx", "0001_schema_contract")]

    operations = [
        migrations.CreateModel(
            name="Artifact",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("logical_class", models.CharField(max_length=64)),
                ("logical_key", models.CharField(max_length=255)),
                ("object_key", models.CharField(max_length=255, unique=True)),
                ("digest_algorithm", models.CharField(default="sha256", max_length=16)),
                ("digest", models.CharField(blank=True, max_length=64)),
                ("size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("declared_mime_type", models.CharField(max_length=255)),
                ("detected_mime_type", models.CharField(blank=True, max_length=255)),
                ("state", models.CharField(choices=[("pending", "Pending"), ("finalized", "Finalized"), ("missing", "Missing"), ("divergent", "Divergent")], default="pending", max_length=16)),
                ("version", models.PositiveIntegerField(default=1)),
                ("safe_error", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="artifact",
            constraint=models.CheckConstraint(condition=models.Q(("size_bytes__isnull", True), ("size_bytes__gte", 0), _connector="OR"), name="nfx_artifact_size_nonnegative_ck"),
        ),
        migrations.AddConstraint(
            model_name="artifact",
            constraint=models.UniqueConstraint(condition=models.Q(("state", "finalized")), fields=("logical_key",), name="nfx_artifact_one_finalized_logical_key_uq"),
        ),
        migrations.AddIndex(
            model_name="artifact",
            index=models.Index(fields=["state", "created_at"], name="nfx_artifact_state_age_ix"),
        ),
        migrations.AddIndex(
            model_name="artifact",
            index=models.Index(fields=["object_key"], name="nfx_artifact_object_key_ix"),
        ),
    ]
