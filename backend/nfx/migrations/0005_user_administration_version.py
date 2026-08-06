from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("nfx", "0004_audit_foundation")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="version",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
