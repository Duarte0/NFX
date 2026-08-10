import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("nfx", "0002_artifact")]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("name", models.CharField(max_length=200)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("administrador", "Administrador"),
                            ("operador", "Operador"),
                            ("visualizador", "Visualizador"),
                        ],
                        max_length=16,
                    ),
                ),
                ("password_hash", models.CharField(max_length=255)),
                ("active", models.BooleanField(default=True)),
                ("revocation_version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="LoginThrottle",
            fields=[
                (
                    "subject_hash",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
                ("failures", models.PositiveIntegerField(default=0)),
                ("next_allowed_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="IdentitySession",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("revocation_version", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_activity_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent_hash", models.CharField(blank=True, max_length=64)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="nfx.user",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="identitysession",
            constraint=models.CheckConstraint(
                condition=models.Q(("expires_at__gte", models.F("created_at"))),
                name="nfx_session_expiry_after_create_ck",
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["active", "role"], name="nfx_user_active_role_ix"),
        ),
        migrations.AddIndex(
            model_name="identitysession",
            index=models.Index(fields=["user", "expires_at"], name="nfx_session_user_exp_ix"),
        ),
        migrations.AddIndex(
            model_name="identitysession",
            index=models.Index(fields=["expires_at"], name="nfx_session_exp_ix"),
        ),
    ]
