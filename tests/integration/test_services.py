from __future__ import annotations

import os

import pytest

from nfx.infrastructure.dependencies import dependencies_from_environment
from nfx.infrastructure.schema import schema_status


@pytest.mark.django_db(transaction=True)
def test_postgres_and_minio_are_reachable_in_an_isolated_run() -> None:
    assert schema_status().compatible, schema_status()
    result = dependencies_from_environment().check()
    assert result.ready, result.unavailable
    assert os.environ["MINIO_BUCKET"].startswith("nfx-p0-test-")
    assert os.environ["TEST_RUN_ID"] in os.environ["MINIO_BUCKET"]
