from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

import boto3
import psycopg

from nfx.infrastructure.configuration import load_settings
from nfx.infrastructure.schema import schema_status


@dataclass(frozen=True)
class DependencyCheck:
    ready: bool
    unavailable: tuple[str, ...]


@dataclass(frozen=True)
class ServiceDependencies:
    database_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    postgres_probe: Callable[[str], None]
    object_probe: Callable[[str, str, str, str], None]
    schema_probe: Callable[[], None]

    def check(self) -> DependencyCheck:
        unavailable: list[str] = []
        try:
            self.postgres_probe(self.database_url)
        except Exception:
            unavailable.append("postgres")
        else:
            try:
                self.schema_probe()
            except Exception:
                unavailable.append("schema")
        try:
            self.object_probe(
                self.minio_endpoint,
                self.minio_access_key,
                self.minio_secret_key,
                self.minio_bucket,
            )
        except Exception:
            unavailable.append("minio")
        return DependencyCheck(not unavailable, tuple(unavailable))


def _postgres_probe(database_url: str) -> None:
    with psycopg.connect(database_url, connect_timeout=2) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")


def _object_probe(endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )
    client.head_bucket(Bucket=bucket)


def _schema_probe() -> None:
    schema_status().require_compatible()


def dependencies_from_environment() -> ServiceDependencies:
    settings = load_settings()
    return ServiceDependencies(
        database_url=settings.secrets.database_url,
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9010"),
        minio_access_key=os.getenv("MINIO_ROOT_USER", "nfx_admin"),
        minio_secret_key=settings.secrets.minio_secret_key,
        minio_bucket=os.getenv("MINIO_BUCKET", "nfx-documentos"),
        postgres_probe=_postgres_probe,
        object_probe=_object_probe,
        schema_probe=_schema_probe,
    )
