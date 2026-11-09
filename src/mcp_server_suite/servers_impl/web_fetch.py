"""Web fetch server: allowlisted domains + in-memory cache.

Network access is injectable: tests pass a fake fetcher, production
uses urllib. Only allowlisted domains can be fetched at all, and EVERY
redirect hop is re-validated against the allowlist (manual redirect
handling — urllib's automatic redirects are disabled in the default
fetcher), so an allowlisted page cannot bounce the client to a
disallowed host.

Fetcher contract: ``fetcher(url)`` returns either a plain string (a
200 response body, used by simple fakes) or a tuple
``(status, headers, body)`` where ``headers`` may carry ``Location``.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlparse

from mcp_server_suite.errors import PolicyError
from mcp_server_suite.protocol import McpServer, Tool

Fetcher = Callable[[str], Any]
DEFAULT_ALLOWLIST: tuple[str, ...] = ("example.com", "example.org")
MAX_REDIRECTS = 5
REDIRECT_STATUSES = (301, 302, 303, 307, 308)

_FETCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "http(s) URL on an allowlisted domain",
        },
    },
    "required": ["url"],
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse automatic redirects so each hop can be re-validated."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str,
                         headers: Any, newurl: str) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _default_fetcher(url: str) -> tuple[int, dict[str, str], str]:
    req = urllib.request.Request(url, headers={"User-Agent": "mcp-server-suite/0.1"})
    try:
        with _OPENER.open(req, timeout=10) as resp:
            body = resp.read(200_000).decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers.items()), body
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000).decode("utf-8", errors="replace")
        headers = dict(exc.headers.items()) if exc.headers else {}
        return exc.code, headers, body


class CachedFetcher:
    """Wrap a fetcher with a dict cache; tracks hit count.

    Allowlist validation runs on the initial URL and on every redirect
    target before that target is fetched.
    """

    def __init__(self, fetcher: Fetcher, allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST) -> None:
        self.fetcher = fetcher
        self.allowlist = allowlist
        self.cache: dict[str, str] = {}
        self.hits = 0

    def _check_allowed(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise PolicyError(f"only http(s) URLs are allowed: {url!r}")
        host = parsed.hostname or ""
        if host not in self.allowlist:
            raise PolicyError(f"domain not allowlisted: {host}")

    def _fetch_once(self, url: str) -> tuple[int, str | None, str]:
        raw = self.fetcher(url)
        if isinstance(raw, tuple):
            status, headers, body = raw
            location = headers.get("Location") or headers.get("location")
            return int(status), location, body
        return 200, None, raw

    def fetch(self, url: str) -> str:
        """Fetch an allowlisted URL, following only allowlisted redirects."""
        if url in self.cache:
            self._check_allowed(url)
            self.hits += 1
            return self.cache[url]
        current = url
        for _hop in range(MAX_REDIRECTS + 1):
            self._check_allowed(current)
            status, location, body = self._fetch_once(current)
            if status in REDIRECT_STATUSES and location:
                current = urljoin(current, location)
                continue
            if status >= 400:
                raise PolicyError(f"fetch failed with HTTP {status} for {current}")
            self.cache[url] = body
            return body
        raise PolicyError(f"too many redirects (>{MAX_REDIRECTS})")


def make_server(fetcher: Fetcher | None = None,
                allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST,
                auth: object = None, bucket: object = None) -> McpServer:
    """Build the web_fetch server."""
    cached = CachedFetcher(fetcher or _default_fetcher, allowlist)

    def fetch_tool(args: dict[str, Any]) -> Any:
        return cached.fetch(str(args.get("url", "")))

    server = McpServer(
        "web_fetch",
        [Tool("fetch", "Fetch an allowlisted URL (cached)", fetch_tool,
              input_schema=_FETCH_SCHEMA)],
        auth=auth, bucket=bucket)
    server.cached_fetcher = cached  # type: ignore[attr-defined]
    return server
