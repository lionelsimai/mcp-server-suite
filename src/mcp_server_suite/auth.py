"""Bearer-token auth shared by all servers (env-configured, no secrets in code)."""

from __future__ import annotations

import hmac
import os

ENV_VAR = "MCP_AUTH_TOKEN"


class AuthValidator:
    """Validate bearer tokens. If no token is configured, auth is disabled
    only for local development — servers log that state at startup."""

    def __init__(self, expected: str | None = None) -> None:
        self.expected = expected if expected is not None else os.environ.get(ENV_VAR, "")

    @property
    def enabled(self) -> bool:
        """True when a token is configured."""
        return bool(self.expected)

    def check(self, provided: str | None) -> bool:
        """Constant-time token comparison."""
        if not self.enabled:
            return True
        if not provided:
            return False
        return hmac.compare_digest(provided, self.expected)
