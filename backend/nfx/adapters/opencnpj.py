from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class OpenCnpjResponse:
    """A safe adapter value; payload is public data and never fiscal authority."""

    status: str
    payload: object = None
    error_code: str = ""


class OpenCnpjClient(Protocol):
    """The only input exposed to OpenCNPJ is the normalized CNPJ."""

    def fetch(self, cnpj: str) -> OpenCnpjResponse: ...


class _HttpResponse(Protocol):
    status: int

    def read(self) -> bytes: ...

    def __enter__(self) -> _HttpResponse: ...

    def __exit__(self, *args: object) -> None: ...


class HttpOpenCnpjClient:
    """Optional public-source transport with an injected opener for tests."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        opener: Callable[..., _HttpResponse] = cast(Callable[..., _HttpResponse], urlopen),
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def fetch(self, cnpj: str) -> OpenCnpjResponse:
        request = Request(
            f"{self.base_url}/{quote(cnpj, safe='')}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                if getattr(response, "status", 200) == 404:
                    return OpenCnpjResponse("not_found")
                try:
                    payload = json.loads(response.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return OpenCnpjResponse("malformed", error_code="resposta_invalida")
                if payload is None:
                    return OpenCnpjResponse("empty")
                if not isinstance(payload, dict | list):
                    return OpenCnpjResponse("malformed", error_code="conteudo_invalido")
                return OpenCnpjResponse("success", payload)
        except HTTPError as exc:
            if exc.code == 404:
                return OpenCnpjResponse("not_found")
            return OpenCnpjResponse("unavailable", error_code="http_erro")


class UnavailableOpenCnpjClient:
    """Default local/runtime adapter until an approved public endpoint is configured."""

    def fetch(self, cnpj: str) -> OpenCnpjResponse:
        # Keep the argument in the contract so an eventual transport cannot receive
        # credentials, user-entered payloads, or fiscal documents by accident.
        if not cnpj:
            return OpenCnpjResponse("malformed", error_code="cnpj_ausente")
        return OpenCnpjResponse("unavailable", error_code="fonte_nao_configurada")
