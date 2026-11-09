"""Entrypoint: run the web_fetch MCP server over stdio.

Usage (from a repo checkout):  python servers/web_fetch/server.py [--allowlist example.net]
Delegates to the suite CLI, so the fail-closed auth policy applies:
set MCP_AUTH_TOKEN, or pass --allow-unauthenticated for local dev.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from mcp_server_suite.cli import main as _cli_main


def main(argv: list[str] | None = None) -> int:
    """Serve web_fetch, forwarding extra CLI arguments."""
    return _cli_main(["serve", "web_fetch", *(argv if argv is not None else sys.argv[1:])])


if __name__ == "__main__":
    raise SystemExit(main())
