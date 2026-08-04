"""Create the non-domain schema contract used by operational readiness."""

from django.db import migrations


class Migration(migrations.Migration):
    """Establish only migration infrastructure; no MVP domain state is created."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE nfx_schema_contract (
                    singleton smallint PRIMARY KEY DEFAULT 1,
                    minimum_compatible_version integer NOT NULL DEFAULT 1,
                    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT nfx_schema_contract_singleton_ck CHECK (singleton = 1),
                    CONSTRAINT nfx_schema_contract_minimum_version_ck
                        CHECK (minimum_compatible_version >= 1)
                );
                INSERT INTO nfx_schema_contract (singleton) VALUES (1);
                CREATE INDEX nfx_schema_contract_updated_at_idx
                    ON nfx_schema_contract (updated_at);
            """,
            reverse_sql="DROP TABLE nfx_schema_contract;",
        )
    ]
