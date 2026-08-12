from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from django.db import connection
from nfx.identity.models import User
from nfx.identity.services import BOOTSTRAP_ADMIN_EMAIL

ROOT = Path(__file__).parents[2]
SECRET = "synthetic-fresh-process-bootstrap-secret"


def _process_environment(password: str | None = SECRET, **overrides: str) -> dict[str, str]:
    environment = os.environ.copy()
    python_path = [str(ROOT / "backend")]
    if environment.get("PYTHONPATH"):
        python_path.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    database_url = urlsplit(environment["DATABASE_URL"])
    environment["DATABASE_URL"] = urlunsplit(
        (
            database_url.scheme,
            database_url.netloc,
            f"/{connection.settings_dict['NAME']}",
            "",
            "",
        )
    )
    environment["NFX_PROFILE"] = "test"
    environment.pop("NFX_PROCESS", None)
    if password is None:
        environment.pop("NFX_BOOTSTRAP_ADMIN_PASSWORD", None)
    else:
        environment["NFX_BOOTSTRAP_ADMIN_PASSWORD"] = password
    environment.update(overrides)
    return environment


def _run_bootstrap(
    password: str | None = SECRET, **overrides: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "backend/manage.py"), "bootstrap_admin"],
        cwd=ROOT,
        env=_process_environment(password, **overrides),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.django_db(transaction=True)
def test_fresh_process_bootstrap_succeeds_and_rerun_preserves_password() -> None:
    first = _run_bootstrap()
    second = _run_bootstrap("synthetic-different-rerun-secret")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert "created" in first.stdout.lower()
    assert "unchanged" in second.stdout.lower()
    assert SECRET not in first.stdout + first.stderr + second.stdout + second.stderr
    assert User.objects.filter(email=BOOTSTRAP_ADMIN_EMAIL).count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("password", [None, "", "   ", "CHANGE_ME_bootstrap"])
def test_fresh_process_rejects_missing_empty_and_placeholder_bootstrap_secret(
    password: str | None,
) -> None:
    result = _run_bootstrap(password)
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "NFX_BOOTSTRAP_ADMIN_PASSWORD" in output
    if password:
        assert password not in output
    assert User.objects.count() == 0


@pytest.mark.parametrize("process", ["web", "worker", "scheduler"])
def test_ordinary_processes_reject_bootstrap_secret_before_settings_are_loaded(
    process: str,
) -> None:
    environment = _process_environment(NFX_PROCESS=process)
    result = subprocess.run(
        [sys.executable, "-c", "import nfx.settings"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "unknown NFX setting" in output
    assert SECRET not in output


def test_bootstrap_boundary_rejects_unsupported_secret_file_configuration() -> None:
    result = _run_bootstrap(NFX_BOOTSTRAP_ADMIN_PASSWORD_FILE="/run/secrets/bootstrap")
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "unknown NFX setting" in output
    assert "NFX_BOOTSTRAP_ADMIN_PASSWORD_FILE" not in output
    assert SECRET not in output
