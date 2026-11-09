"""Filesystem server: jailed read/list only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp_server_suite.errors import JailError, PolicyError
from mcp_server_suite.protocol import McpServer, Tool

MAX_READ_BYTES = 64_000


def make_server(root: Path, auth: object = None, bucket: object = None) -> McpServer:
    """Build the filesystem_safe server jailed to ``root``."""
    jail = Path(root).resolve()
    jail.mkdir(parents=True, exist_ok=True)

    def _resolve(args: dict[str, Any]) -> Path:
        rel = str(args.get("path", "."))
        target = (jail / rel).resolve()
        if not str(target).startswith(str(jail)):
            raise JailError(f"path escapes jail: {rel!r}")
        return target

    def list_dir(args: dict[str, Any]) -> Any:
        target = _resolve(args)
        if not target.is_dir():
            raise PolicyError(f"not a directory: {args.get('path')}")
        return sorted(p.name for p in target.iterdir())

    def read_file(args: dict[str, Any]) -> Any:
        target = _resolve(args)
        if not target.is_file():
            raise PolicyError(f"not a file: {args.get('path')}")
        data = target.read_bytes()[:MAX_READ_BYTES]
        return data.decode("utf-8", errors="replace")

    tools = [
        Tool("list_dir", "List a directory inside the jail", list_dir),
        Tool("read_file", "Read a text file inside the jail (64KB cap)", read_file),
    ]
    return McpServer("filesystem_safe", tools, auth=auth, bucket=bucket)
