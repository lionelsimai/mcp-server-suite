"""Tests for mcp-server-suite."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from mcp_server_suite.auth import AuthValidator
from mcp_server_suite.cli import main
from mcp_server_suite.errors import JailError, PolicyError
from mcp_server_suite.protocol import McpServer, Tool
from mcp_server_suite.rate_limit import TokenBucket
from mcp_server_suite.servers_impl import filesystem_safe, sqlite_query, web_fetch


def call(server: McpServer, tool: str, args: dict, token: str | None = None) -> dict:
    params: dict = {"name": tool, "arguments": args}
    if token:
        params["_meta"] = {"token": token}
    return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params})

def is_error(resp: dict) -> bool:
    """0.1.1 semantics: tool failures are results with isError=true,
    not JSON-RPC protocol errors (the pre-0.1.1 tests asserted the old,
    audited behaviour)."""
    return resp.get("result", {}).get("isError") is True

def test_protocol_initialize() -> None:
    s = McpServer("x", [])
    r = s.handle({"id": 1, "method": "initialize", "params": {}})
    assert r["result"]["serverInfo"]["name"] == "x"

def test_protocol_ping_and_unknown() -> None:
    s = McpServer("x", [])
    assert s.handle({"id": 1, "method": "ping"})["result"] == {}
    assert "error" in s.handle({"id": 1, "method": "nope"})

def test_tools_list_and_call() -> None:
    s = McpServer("x", [Tool("echo", "echo", lambda a: a.get("v", ""))])
    names = [t["name"] for t in s.handle({"id": 1, "method": "tools/list"})["result"]["tools"]]
    assert names == ["echo"]
    out = call(s, "echo", {"v": "hi"})
    assert out["result"]["content"][0]["text"] == "hi"

def test_auth_blocks_wrong_token(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("secret-data")
    s = filesystem_safe.make_server(tmp_path, auth=AuthValidator("good"))
    assert "error" in call(s, "read_file", {"path": "a.txt"}, token="bad")
    assert "result" in call(s, "read_file", {"path": "a.txt"}, token="good")

def test_auth_disabled_without_token(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("open")
    s = filesystem_safe.make_server(tmp_path, auth=AuthValidator(""))
    assert "result" in call(s, "read_file", {"path": "a.txt"})

def test_rate_limit_bucket() -> None:
    now = [1000.0]
    b = TokenBucket(capacity=2, refill_per_s=0.0, clock=lambda: now[0])
    assert b.allow() and b.allow() and not b.allow()
    now[0] += 10  # no refill configured, still blocked
    b2 = TokenBucket(capacity=1, refill_per_s=1.0, clock=lambda: now[0])
    assert b2.allow() and not b2.allow()
    now[0] += 2
    assert b2.allow()

def test_rate_limit_in_server(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    bucket = TokenBucket(capacity=1, refill_per_s=0.0, clock=lambda: 0.0)
    s = filesystem_safe.make_server(tmp_path, bucket=bucket)
    assert "result" in call(s, "read_file", {"path": "a.txt"})
    assert call(s, "read_file", {"path": "a.txt"})["error"]["code"] == -32002

def test_filesystem_list_and_read(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("world")
    s = filesystem_safe.make_server(tmp_path)
    listed = call(s, "list_dir", {"path": "."})
    assert "hello.txt" in listed["result"]["content"][0]["text"]
    read = call(s, "read_file", {"path": "hello.txt"})
    assert read["result"]["content"][0]["text"] == "world"

def test_filesystem_jail_escape(tmp_path: Path) -> None:
    s = filesystem_safe.make_server(tmp_path)
    r = call(s, "read_file", {"path": "../../etc/passwd"})
    assert is_error(r)

def test_filesystem_missing_file(tmp_path: Path) -> None:
    s = filesystem_safe.make_server(tmp_path)
    assert is_error(call(s, "read_file", {"path": "ghost.txt"}))

def test_web_fetch_allowlist_and_cache() -> None:
    calls = {"n": 0}
    def fake(url: str) -> str:
        calls["n"] += 1
        return "content"
    s = web_fetch.make_server(fetcher=fake)
    assert "result" in call(s, "fetch", {"url": "https://example.com/x"})
    assert "result" in call(s, "fetch", {"url": "https://example.com/x"})
    assert calls["n"] == 1  # second served from cache
    assert is_error(call(s, "fetch", {"url": "https://evil.test/x"}))

@pytest.fixture()
def db(tmp_path: Path) -> Path:
    p = tmp_path / "t.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE t (id INTEGER, name TEXT)")
    c.executemany("INSERT INTO t VALUES (?, ?)", [(1, "a"), (2, "b")])
    c.commit()
    c.close()
    return p

def test_sqlite_read_only_ok(db: Path) -> None:
    s = sqlite_query.make_server(db)
    r = call(s, "query", {"sql": "SELECT name FROM t ORDER BY id"})
    assert "alpha" not in r["result"]["content"][0]["text"]
    assert '"a"' in r["result"]["content"][0]["text"]

@pytest.mark.parametrize("sql", [
    "DELETE FROM t", "INSERT INTO t VALUES (3, 'x')", "UPDATE t SET name='x'",
    "DROP TABLE t", "SELECT 1; SELECT 2",
])
def test_sqlite_blocks_writes(db: Path, sql: str) -> None:
    s = sqlite_query.make_server(db)
    assert is_error(call(s, "query", {"sql": sql}))

def test_sqlite_validator_direct() -> None:
    with pytest.raises(PolicyError):
        sqlite_query.assert_read_only("delete from t")

def test_jail_error_type() -> None:
    assert JailError("x").code == -32003
    assert PolicyError("x").code == -32004

def test_cli_list(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "filesystem_safe" in out and "sqlite_query" in out

def test_cli_demo_e2e(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "hello from filesystem_safe" in out and "write blocked" in out

def test_real_time_bucket_refills() -> None:
    b = TokenBucket(capacity=1, refill_per_s=50.0)
    assert b.allow()
    time.sleep(0.05)
    assert b.allow()
