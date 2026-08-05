from __future__ import annotations

import threading

import pytest
from django.db import connections
from django.db.migrations import Migration
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.operations.special import RunSQL
from django.db.migrations.recorder import MigrationRecorder

from nfx.infrastructure.schema import SchemaMigrator, schema_status


def _unapply_nfx_migrations() -> None:
    executor = MigrationExecutor(connections["default"])
    executor.migrate([("nfx", None)])


@pytest.mark.django_db(transaction=True)
def test_clean_install_and_rerun_produce_the_same_schema() -> None:
    _unapply_nfx_migrations()

    first = SchemaMigrator().migrate()
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'nfx_schema_contract'::regclass ORDER BY conname"
        )
        constraints = tuple(row[0] for row in cursor.fetchall())
        cursor.execute(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'nfx_schema_contract' ORDER BY indexname"
        )
        indexes = tuple(row[0] for row in cursor.fetchall())

    second = SchemaMigrator().migrate()

    assert first.applied == (
        "nfx.0001_schema_contract",
        "nfx.0002_artifact",
        "nfx.0003_identity",
    )
    assert second.applied == ()
    assert constraints == (
        "nfx_schema_contract_minimum_version_ck",
        "nfx_schema_contract_pkey",
        "nfx_schema_contract_singleton_ck",
    )
    assert indexes == ("nfx_schema_contract_pkey", "nfx_schema_contract_updated_at_idx")
    assert schema_status().compatible


@pytest.mark.django_db(transaction=True)
def test_failed_migration_is_not_recorded_and_a_safe_correction_can_continue() -> None:
    _unapply_nfx_migrations()
    failing_key = ("nfx", "0002_test_failure")
    failing = Migration(failing_key[1], failing_key[0])
    failing.dependencies = [("nfx", "0001_schema_contract")]
    failing.operations = [
        RunSQL(
            "CREATE TABLE nfx_migration_failure_probe (id integer); SELECT 1 / 0;",
            "DROP TABLE IF EXISTS nfx_migration_failure_probe;",
        )
    ]
    executor = MigrationExecutor(connections["default"])
    executor.loader.disk_migrations[failing_key] = failing
    executor.loader.build_graph()

    with pytest.raises(Exception):
        executor.migrate([failing_key])

    applied = MigrationRecorder(connections["default"]).applied_migrations()
    assert failing_key not in applied
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT to_regclass('nfx_migration_failure_probe')")
        assert cursor.fetchone() == (None,)

    correction = SchemaMigrator().migrate()

    assert correction.applied == (
        "nfx.0001_schema_contract",
        "nfx.0002_artifact",
        "nfx.0003_identity",
    )
    assert schema_status().compatible


@pytest.mark.django_db(transaction=True)
def test_two_migrators_are_serialized_and_only_one_applies_the_baseline() -> None:
    _unapply_nfx_migrations()
    barrier = threading.Barrier(2)
    outcomes: list[tuple[str, ...]] = []
    failures: list[BaseException] = []

    def migrate_in_parallel() -> None:
        try:
            connection = connections["default"]
            barrier.wait()
            outcomes.append(SchemaMigrator(connection).migrate().applied)
        except BaseException as exc:  # pragma: no cover - asserted by the caller
            failures.append(exc)
        finally:
            connections.close_all()

    first = threading.Thread(target=migrate_in_parallel)
    second = threading.Thread(target=migrate_in_parallel)
    first.start()
    second.start()
    first.join()
    second.join()

    assert not failures
    assert sorted(outcomes) == [
        (),
        ("nfx.0001_schema_contract", "nfx.0002_artifact", "nfx.0003_identity"),
    ]
    assert schema_status().compatible


@pytest.mark.django_db(transaction=True)
def test_schema_status_detects_ahead_incompatible_history() -> None:
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) "
            "VALUES ('nfx', '9999_future_incompatible', CURRENT_TIMESTAMP)"
        )
    status = schema_status()

    assert status.unexpected == ("9999_future_incompatible",)
    assert not status.compatible
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'nfx' AND name = '9999_future_incompatible'"
        )
