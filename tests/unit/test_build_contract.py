from __future__ import annotations

import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def clean_build_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("NFX_") or name in {"DATABASE_URL", "MINIO_ROOT_PASSWORD"}:
            environment.pop(name)
    return environment


def test_make_build_succeeds_without_services_or_ambient_configuration(tmp_path: Path) -> None:
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        """
import socket


def block_network(*args, **kwargs):
    raise AssertionError("make build attempted network I/O")


socket.socket.connect = block_network
socket.create_connection = block_network
""",
        encoding="utf-8",
    )
    environment = clean_build_environment()
    environment["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        ["make", "build"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (ROOT / "frontend" / "dist" / "index.html").is_file()
    assert "synthetic-test-django-secret" not in result.stdout + result.stderr
    assert "nfx-test-only-password" not in result.stdout + result.stderr


def test_invalid_build_configuration_fails_before_frontend_step(tmp_path: Path) -> None:
    marker = tmp_path / "npm-was-called"
    fake_npm = tmp_path / "npm"
    fake_npm.write_text(
        f"#!/bin/sh\nprintf '%s' called > {marker}\n",
        encoding="utf-8",
    )
    fake_npm.chmod(fake_npm.stat().st_mode | stat.S_IXUSR)

    invalid_python = tmp_path / "python-with-invalid-config"
    invalid_python.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                "unset NFX_PROFILE NFX_SECRET_KEY NFX_CERTIFICATE_MASTER_KEY",
                "unset DATABASE_URL MINIO_ROOT_PASSWORD",
                f'exec {shlex.quote(sys.executable)} "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    invalid_python.chmod(invalid_python.stat().st_mode | stat.S_IXUSR)

    environment = clean_build_environment()
    real_path = os.environ.get("PATH", "")
    environment["PATH"] = f"{tmp_path}{os.pathsep}{real_path}"

    result = subprocess.run(
        ["make", "build", f"PYTHON={invalid_python}"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "NFX_PROFILE" in result.stderr
    assert not marker.exists()
