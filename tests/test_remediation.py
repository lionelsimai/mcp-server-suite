"""Remediation tests (0.1.1): one per audit fix for mcp-server-suite."""
from __future__ import annotations

import io
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from test_mcp_suite import call, is_error

from mcp_server_suite.cli import main
from mcp_server_suite.protocol import McpServer, Tool
from mcp_server_suite.servers_impl import filesystem_safe, sqlite_query, web_fetch
from mcp_server_suite.servers_impl.web_fetch import CachedFetcher


def _tools(server: McpServer) -> list[dict]:
    resp = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert resp is not None
    return resp["result"]["tools"]


@pytest.mark.parametrize("make", ["fs", "wf", "sq"])
def test_every_tool_has_real_input_schema(tmp_path: Path, make: str) -> None:
    if make == "fs":
        server = filesystem_safe.make_server(tmp_path)
    elif make == "wf":
        server = web_fetch.make_server(fetcher=lambda url: "x")
    else:
        db = tmp_path / "t.db"
        sqlite3.connect(db).close()
        server = sqlite_query.make_server(db)
    for tool in _tools(server):
        schema = tool["inputSchema"]
        assert schema["properties"], f"{tool['name']} has an empty schema"
        assert schema["required"], f"{tool['name']} declares no required args"
        for prop in schema["properties"].values():
            assert prop["type"] == "string"


def test_notification_gets_no_response() -> None:
    s = McpServer("x", [])
    assert s.handle({"method": "notifications/initialized", "params": {}}) is None
    assert s.handle({"method": "notifications/cancelled", "params": {}}) is None
    assert s.handle({"jsonrpc": "2.0", "method": "ping"}) is None  # no id at all


def test_malformed_line_survives_stdio(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    s = McpServer("x", [])
    lines = "{not json\n" + json.dumps({"jsonrpc": "2.0", "id": 7, "method": "ping"}) + "\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(lines))
    s.serve_stdio()
    out = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert out[0]["error"]["code"] == -32700 and out[0]["id"] is None
    assert out[1]["id"] == 7 and out[1]["result"] == {}


def test_tool_exception_is_iserror_without_leak(tmp_path: Path) -> None:
    def boom(args: dict) -> object:
        raise RuntimeError("internal secret path /srv/private/db")

    s = McpServer("x", [Tool("boom", "explodes", boom)])
    resp = call(s, "boom", {})
    assert is_error(resp)
    assert "private" not in resp["result"]["content"][0]["text"]


def test_sibling_prefix_jail_escape(tmp_path: Path) -> None:
    jail = tmp_path / "jail"
    evil = tmp_path / "jail-evil"
    evil.mkdir(parents=True)
    (evil / "secret.txt").write_text("sibling secret")
    s = filesystem_safe.make_server(jail)
    assert is_error(call(s, "read_file", {"path": "../jail-evil/secret.txt"}))


def test_redirect_to_disallowed_host_blocked() -> None:
    def fake(url: str) -> tuple[int, dict[str, str], str]:
        if url == "https://example.com/start":
            return 302, {"Location": "https://evil.test/steal"}, ""
        return 200, {}, "should never be fetched"

    s = web_fetch.make_server(fetcher=fake)
    assert is_error(call(s, "fetch", {"url": "https://example.com/start"}))


def test_redirect_to_allowlisted_host_followed() -> None:
    def fake(url: str) -> tuple[int, dict[str, str], str]:
        if url == "https://example.com/start":
            return 302, {"Location": "https://example.org/final"}, ""
        return 200, {}, "final content"

    s = web_fetch.make_server(fetcher=fake)
    resp = call(s, "fetch", {"url": "https://example.com/start"})
    assert resp["result"]["content"][0]["text"] == "final content"


def test_non_http_scheme_blocked() -> None:
    fetcher = CachedFetcher(lambda url: "x")
    with pytest.raises(Exception, match="http"):
        fetcher.fetch("file:///etc/passwd")


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    p = tmp_path / "t.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    c.execute("INSERT INTO t VALUES (1, 'a')")
    c.commit()
    c.close()
    return p


def test_sqlite_pragma_function_blocked(db: Path) -> None:
    s = sqlite_query.make_server(db)
    assert is_error(call(s, "query", {"sql": "SELECT * FROM pragma_table_info('t')"}))
    assert is_error(call(s, "query", {"sql": "SELECT name FROM pragma_database_list()"}))


def test_serve_fails_closed_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    assert main(["serve", "filesystem_safe"]) == 2


def test_serve_allow_unauthenticated_and_allowlist(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))  # immediate EOF
    code = main(["serve", "web_fetch", "--allow-unauthenticated",
                 "--allowlist", "example.net"])
    assert code == 0
    assert "WITHOUT authentication" in capsys.readouterr().err
