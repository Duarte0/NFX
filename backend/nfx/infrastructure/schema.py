"""Schema compatibility and serialized migration support.

This module deliberately owns only infrastructure metadata.  Domain specs add
their own tables and migrations; this baseline only makes their migration
history observable and safe to operate.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

logger = logging.getLogger(__name__)

# Stable, application-specific PostgreSQL advisory-lock key.  It serializes
# deploy-time schema changes without turning normal application writes into a
# global lock.
MIGRATION_LOCK_KEY = 5_012_025_001
SCHEMA_APP_LABEL = "nfx"


class SchemaIncompatibleError(RuntimeError):
    """Raised when the database cannot safely serve this application version."""


@dataclass(frozen=True)
class SchemaStatus:
    required: tuple[str, ...]
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]

    @property
    def compatible(self) -> bool:
        return not self.missing and not self.unexpected

    def require_compatible(self) -> None:
        if not self.compatible:
            raise SchemaIncompatibleError("Database schema is incompatible")


@dataclass(frozen=True)
class MigrationOutcome:
    applied: tuple[str, ...]


def _migration_names(connection: BaseDatabaseWrapper) -> tuple[str, ...]:
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    names = {
        name
        for app_label, name in loader.graph.nodes
        if app_label == SCHEMA_APP_LABEL
    }
    return tuple(sorted(names))


def schema_status(connection: BaseDatabaseWrapper | None = None) -> SchemaStatus:
    """Compare the installed NFX migration graph with its persisted history."""
    database = connection or connections["default"]
    required = _migration_names(database)
    applied = {
        name
        for app_label, name in MigrationRecorder(database).applied_migrations()
        if app_label == SCHEMA_APP_LABEL
    }
    return SchemaStatus(
        required=required,
        missing=tuple(name for name in required if name not in applied),
        unexpected=tuple(sorted(applied - set(required))),
    )


class SchemaMigrator:
    """Run Django migrations once at a time and report only safe metadata."""

    def __init__(
        self,
        connection: BaseDatabaseWrapper | None = None,
        executor_factory: Callable[[BaseDatabaseWrapper], MigrationExecutor] = MigrationExecutor,
    ) -> None:
        self.connection = connection or connections["default"]
        self.executor_factory = executor_factory

    def migrate(self) -> MigrationOutcome:
        self.connection.ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_KEY])
        try:
            executor = self.executor_factory(self.connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
            names = tuple(f"{migration.app_label}.{migration.name}" for migration, _ in plan)
            logger.info("schema_migration_started", extra={"migrations": names, "result": "started"})
            executor.migrate(targets)
            logger.info("schema_migration_finished", extra={"migrations": names, "result": "success"})
            return MigrationOutcome(applied=names)
        except Exception:
            logger.exception("schema_migration_finished", extra={"result": "failure"})
            raise
        finally:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_KEY])
