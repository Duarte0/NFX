"""P0 fiscal boundary: validate every destination before a transport can run."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from nfx.infrastructure.configuration import PublicSettings, _validate_destination


class FiscalDestinationError(RuntimeError):
    """Safe rejection that intentionally contains no destination value."""


@dataclass(frozen=True)
class EmptyFiscalSimulator:
    """The sole initial fiscal transport; it always produces an empty result."""

    def collect(self) -> tuple[()]:
        return ()


class FiscalDestinationGuard:
    def __init__(self, settings: PublicSettings) -> None:
        self._settings = settings

    def validate(self, destination: str) -> str:
        try:
            normalized = _validate_destination(destination, "fiscal destination")
        except RuntimeError as exc:
            raise FiscalDestinationError("Fiscal destination rejected") from exc
        is_local_profile = self._settings.profile in {"test", "development"}
        if is_local_profile or normalized not in self._settings.fiscal_allowlist:
            raise FiscalDestinationError("Fiscal destination rejected")
        return normalized

    def send(
        self,
        destination: str,
        sender: Callable[[str], object],
        redirects: Sequence[str] = (),
    ) -> object:
        """Validate the configured URL and every declared redirect before I/O."""
        normalized = self.validate(destination)
        for redirect in redirects:
            self.validate(redirect)
        return sender(normalized)
