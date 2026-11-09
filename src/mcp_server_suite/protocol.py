"""Minimal MCP-over-stdio JSON-RPC protocol (no external SDK needed).

Implements the subset agents actually use: initialize, ping,
tools/list and tools/call, with auth and rate-limit gates applied
uniformly before dispatch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class ToolHandler(Protocol):
    """A tool callable."""

    def __call__(self, args: dict[str, Any]) -> Any:
        """Run the tool."""
        ...


@dataclass
class Tool:
    """An MCP tool definition."""

    name: str
    description: str
    handler: ToolHandler
    input_schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )


class McpServer:
    """A minimal, testable MCP server core."""

    def __init__(self, name: str, tools: list[Tool], auth: object = None,
                 bucket: object = None) -> None:
        self.name = name
        self.tools = {t.name: t for t in tools}
        self.auth = auth
        self.bucket = bucket

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle one JSON-RPC request dict and return the response dict."""
        req_id = request.get("id", 1)
        method = request.get("method", "")
        params: dict[str, Any] = request.get("params") or {}
        # Auth gate (initialize may carry _meta.token; tools/call must).
        if self.auth is not None and method in {"tools/call", "tools/list"}:
            token = (params.get("_meta") or {}).get("token")
            if not self.auth.check(token):  # type: ignore[attr-defined]
                return self._err(req_id, -32001, "unauthorized: bad or missing token")
        if self.bucket is not None and method == "tools/call":
            if not self.bucket.allow():  # type: ignore[attr-defined]
                return self._err(req_id, -32002, "rate limit exceeded")
        try:
            if method == "initialize":
                return self._ok(req_id, {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.name, "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                })
            if method == "ping":
                return self._ok(req_id, {})
            if method == "tools/list":
                return self._ok(req_id, {"tools": [
                    {"name": t.name, "description": t.description,
                     "inputSchema": t.input_schema}
                    for t in self.tools.values()
                ]})
            if method == "tools/call":
                tool_name = params.get("name", "")
                tool = self.tools.get(tool_name)
                if tool is None:
                    return self._err(req_id, -32601, f"unknown tool: {tool_name}")
                result = tool.handler(params.get("arguments") or {})
                text = result if isinstance(result, str) else json.dumps(result)
                return self._ok(req_id, {"content": [{"type": "text", "text": text}]})
            return self._err(req_id, -32601, f"unknown method: {method}")
        except Exception as exc:  # structured surface, never a stack leak
            code = getattr(exc, "code", -32000)
            return self._err(req_id, int(code), str(exc))

    @staticmethod
    def _ok(req_id: object, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _err(req_id: object, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def serve_stdio(self) -> None:  # pragma: no cover - manual/integration use
        """Serve newline-delimited JSON-RPC on stdin/stdout."""
        import sys

        for line in sys.stdin:
            if line.strip():
                response = self.handle(json.loads(line))
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
