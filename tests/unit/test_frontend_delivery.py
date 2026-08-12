from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from mimetypes import guess_type
from pathlib import Path

import pytest
from django.test import Client


def frontend_urls() -> object:
    return import_module("nfx.urls")


def make_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, bytes, bytes]:
    distribution = tmp_path / "dist"
    assets = distribution / "assets"
    assets.mkdir(parents=True)
    index = (
        b'<html><head><link rel="stylesheet" href="/assets/app.css"></head>'
        b'<body><div id="root"></div><script type="module" src="/assets/app.js"></script>'
        b"</body></html>"
    )
    javascript = b"console.log('synthetic build');"
    (distribution / "index.html").write_bytes(index)
    (assets / "app.css").write_text("#root { color: #1f2937; }", encoding="utf-8")
    (assets / "app.js").write_bytes(javascript)
    monkeypatch.setattr(frontend_urls(), "FRONTEND_DIST", distribution)
    return distribution, index, javascript


def test_root_serves_build_html_and_every_referenced_asset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    distribution, index, javascript = make_build(monkeypatch, tmp_path)
    client = Client()

    root = client.get("/")

    assert root.status_code == 200
    assert root["Content-Type"].split(";", 1)[0] == "text/html"
    assert root.content == index
    assert b"NFX INOV foundation" not in root.content

    asset_urls = re.findall(rb'(?:src|href)="(/assets/[^\"]+)"', root.content)
    assert asset_urls == [b"/assets/app.css", b"/assets/app.js"]
    for asset_url in asset_urls:
        response = client.get(asset_url.decode("ascii"))
        expected_type = guess_type(asset_url.decode("ascii"))[0]
        assert response.status_code == 200
        assert response["Content-Type"].split(";", 1)[0] == expected_type

    assert client.get("/assets/app.js").content == javascript
    assert distribution.joinpath("index.html").read_bytes() == index


def test_missing_or_escaped_distribution_returns_safe_503(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing-dist"
    monkeypatch.setattr(frontend_urls(), "FRONTEND_DIST", missing)

    response = Client().get("/")

    assert response.status_code == 503
    assert response.content == "Frontend build não encontrado.".encode()
    assert str(tmp_path).encode() not in response.content
    assert b"NFX INOV foundation" not in response.content

    unreadable = tmp_path / "unreadable-dist"
    (unreadable / "index.html").mkdir(parents=True)
    monkeypatch.setattr(frontend_urls(), "FRONTEND_DIST", unreadable)
    assert Client().get("/").status_code == 503

    unreadable_file = tmp_path / "unreadable-file-dist"
    unreadable_file.mkdir()
    (unreadable_file / "index.html").write_text("<html>unreadable</html>", encoding="utf-8")
    original_read_bytes = Path.read_bytes

    def fail_index_read(path: Path) -> bytes:
        if path == unreadable_file / "index.html":
            raise OSError("synthetic read failure")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_index_read)
    monkeypatch.setattr(frontend_urls(), "FRONTEND_DIST", unreadable_file)
    assert Client().get("/").status_code == 503

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "index.html").write_text("<html>outside</html>", encoding="utf-8")
    escaped_distribution = tmp_path / "dist-link"
    escaped_distribution.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(frontend_urls(), "FRONTEND_DIST", escaped_distribution)

    assert Client().get("/").status_code == 503


@pytest.mark.parametrize(
    "request_path",
    [
        "/assets/missing.js",
        "/assets/assets/app.js",
        "/assets/../index.html",
        "/assets/",
        "/assets/app.css/child",
        "/src/main.tsx",
    ],
)
def test_invalid_assets_are_not_served(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, request_path: str
) -> None:
    distribution, _, _ = make_build(monkeypatch, tmp_path)
    nested_assets = distribution / "assets" / "assets"
    nested_assets.mkdir()
    (nested_assets / "app.js").write_bytes(b"repeated-prefix must not be served")

    response = Client().get(request_path)

    assert response.status_code == 404
    assert str(tmp_path).encode() not in response.content
    assert b"NFX INOV foundation" not in response.content


def test_asset_symlink_and_symlinked_asset_directory_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    distribution, _, _ = make_build(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.js").write_bytes(b"outside build")
    (distribution / "assets" / "escaped.js").symlink_to(outside / "secret.js")

    assert Client().get("/assets/escaped.js").status_code == 404

    real_assets = distribution / "assets"
    real_assets.rename(distribution / "assets-real")
    real_assets.symlink_to(outside, target_is_directory=True)
    assert Client().get("/assets/secret.js").status_code == 404


def test_root_assets_and_session_routes_are_read_only_and_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    distribution, _, javascript = make_build(monkeypatch, tmp_path)
    before = sorted(
        (
            path.relative_to(distribution).as_posix(),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in distribution.rglob("*")
        if path.is_file()
    )

    def read_responses(_: int) -> tuple[int, bytes, int, dict[str, object]]:
        client = Client()
        root = client.get("/")
        asset = client.get("/assets/app.js")
        session = client.get("/api/auth/session")
        return root.status_code, asset.content, session.status_code, session.json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(read_responses, range(12)))

    assert responses == [(200, javascript, 401, {"detail": "Não autenticado."})] * 12
    assert Client().get("/health/live").json() == {"status": "live"}
    after = sorted(
        (
            path.relative_to(distribution).as_posix(),
            path.stat().st_size,
            path.stat().st_mtime_ns,
        )
        for path in distribution.rglob("*")
        if path.is_file()
    )
    assert after == before
