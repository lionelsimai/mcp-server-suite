"""Web fetch server: allowlisted domains + in-memory cache.

Network access is injectable: tests pass a fake fetcher, production uses
urllib. Only allowlisted domains can be fetched at all.
"""

from __future__ import annotations

import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from mcp_server_suite.errors import PolicyError
from mcp_server_suite.protocol import McpServer, Tool

Fetcher = Callable[[str], str]
DEFAULT_ALLOWLIST: tuple[str, ...] = ("example.com", "example.org")


def _default_fetcher(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "mcp-server-suite/0.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read(200_000).decode("utf-8", errors="replace")


class CachedFetcher:
    """Wrap a fetcher with a simple dict cache; tracks hit count."""

    def __init__(self, fetcher: Fetcher, allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST) -> None:
        self.fetcher = fetcher
        self.allowlist = allowlist
        self.cache: dict[str, str] = {}
        self.hits = 0

    def fetch(self, url: str) -> str:
        """Fetch an allowlisted URL, serving repeats from cache."""
        host = urlparse(url).hostname or ""
        if host not in self.allowlist:
            raise PolicyError(f"domain not allowlisted: {host}")
        if url in self.cache:
            self.hits += 1
            return self.cache[url]
        text = self.fetcher(url)
        self.cache[url] = text
        return text


def make_server(fetcher: Fetcher | None = None,
                allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST,
                auth: object = None, bucket: object = None) -> McpServer:
    """Build the web_fetch server."""
    cached = CachedFetcher(fetcher or _default_fetcher, allowlist)

    def fetch_tool(args: dict[str, Any]) -> Any:
        return cached.fetch(str(args.get("url", "")))

    server = McpServer("web_fetch", [Tool("fetch", "Fetch an allowlisted URL (cached)", fetch_tool)],
                       auth=auth, bucket=bucket)
    server.cached_fetcher = cached  # type: ignore[attr-defined]
    return server
