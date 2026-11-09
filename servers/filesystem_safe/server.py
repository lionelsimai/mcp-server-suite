"""Entrypoint: run the filesystem_safe MCP server over stdio.

Usage (from a repo checkout):  python servers/filesystem_safe/server.py [--root DIR]
Delegates to the suite CLI, so the fail-closed auth policy applies:
set MCP_AUTH_TOKEN, or pass --allow-unauthenticated for local dev.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp_server_suite.cli import main as _cli_main


def main(argv: list[str] | None = None) -> int:
    """Serve filesystem_safe, forwarding extra CLI arguments."""
    return _cli_main(["serve", "filesystem_safe", *(argv if argv is not None else sys.argv[1:])])


if __name__ == "__main__":
    raise SystemExit(main())
