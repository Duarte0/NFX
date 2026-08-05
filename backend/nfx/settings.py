from __future__ import annotations

import os
from urllib.parse import urlparse

from nfx.infrastructure.configuration import load_settings

NFX_SETTINGS = load_settings()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = NFX_SETTINGS.secrets.django_secret_key
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
ROOT_URLCONF = "nfx.urls"
WSGI_APPLICATION = "nfx.wsgi.application"
ASGI_APPLICATION = "nfx.asgi.application"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "nfx",
]
MIDDLEWARE = [
    "nfx.infrastructure.http.CorrelationIdMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
TEMPLATES: list[dict[str, object]] = []
USE_TZ = True
TIME_ZONE = "America/Sao_Paulo"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False


def _database_from_url(value: str) -> dict[str, object]:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must use PostgreSQL")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or 5432,
    }


DATABASES = {"default": _database_from_url(NFX_SETTINGS.secrets.database_url)}
