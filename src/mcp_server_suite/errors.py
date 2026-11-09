"""Structured errors."""

from __future__ import annotations


class McpError(Exception):
    """Base error with a JSON-RPC error code."""

    code = -32000

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthError(McpError):
    """Authentication failed."""

    code = -32001


class RateLimitError(McpError):
    """Rate limit exceeded."""

    code = -32002


class JailError(McpError):
    """Path escapes the allowed root."""

    code = -32003


class PolicyError(McpError):
    """Request violates server policy (domain, SQL, size)."""

    code = -32004
