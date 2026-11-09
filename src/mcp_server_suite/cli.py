"""Command-line interface for mcp-server-suite."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp_server_suite.auth import AuthValidator
from mcp_server_suite.rate_limit import TokenBucket
from mcp_server_suite.servers_impl import filesystem_safe, sqlite_query, web_fetch

SERVERS = ("filesystem_safe", "web_fetch", "sqlite_query")


def _call(server: Any, tool: str, args: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"name": tool, "arguments": args}
    if token:
        params["_meta"] = {"token": token}
    return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params})


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(prog="mcp-suite", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List the bundled servers")
    sub.add_parser("demo", help="Offline demo of all 3 servers (no network)")
    serve = sub.add_parser("serve", help="Serve one server over stdio")
    serve.add_argument("server", choices=list(SERVERS))
    serve.add_argument("--root", default=".")
    serve.add_argument("--db", default="demo.db")
    return parser


def run_demo() -> int:
    """Run the offline demo and return an exit code."""
    token = "demo-token"
    auth = AuthValidator(token)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "hello.txt").write_text("hello from filesystem_safe", encoding="utf-8")
        fs = filesystem_safe.make_server(root, auth=auth, bucket=TokenBucket(50, 50))
        print("filesystem_safe tools:", [t["name"] for t in fs.handle(
            {"id": 1, "method": "tools/list", "params": {"_meta": {"token": token}}})["result"]["tools"]])
        print("filesystem_safe read:", _call(fs, "read_file", {"path": "hello.txt"}, token)
              ["result"]["content"][0]["text"])
        calls = {"n": 0}

        def fake_fetch(url: str) -> str:
            calls["n"] += 1
            return f"<html>fetched {url}</html>"

        wf = web_fetch.make_server(fetcher=fake_fetch, auth=auth, bucket=TokenBucket(50, 50))
        print("web_fetch first:", _call(wf, "fetch", {"url": "https://example.com/a"}, token)
              ["result"]["content"][0]["text"])
        print("web_fetch cached:", _call(wf, "fetch", {"url": "https://example.com/a"}, token)
              ["result"]["content"][0]["text"], f"(network calls: {calls['n']})")
        db = root / "demo.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE items (id INTEGER, name TEXT)")
        conn.executemany("INSERT INTO items VALUES (?, ?)", [(1, "alpha"), (2, "beta")])
        conn.commit()
        conn.close()
        sq = sqlite_query.make_server(db, auth=auth, bucket=TokenBucket(50, 50))
        result = _call(sq, "query", {"sql": "SELECT name FROM items ORDER BY id"}, token)
        print("sqlite_query result:", result["result"]["content"][0]["text"])
        blocked = _call(sq, "query", {"sql": "DELETE FROM items"}, token)
        print("sqlite_query write blocked:", blocked["error"]["message"])
        unauth = _call(fs, "read_file", {"path": "hello.txt"}, token="wrong")
        print("auth check (wrong token):", unauth["error"]["message"])
    print(json.dumps({"servers": list(SERVERS), "demo": "ok"}))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        for name in SERVERS:
            print(name)
        return 0
    if args.cmd == "demo":
        return run_demo()
    auth = AuthValidator()
    bucket = TokenBucket()
    server: Any
    if args.server == "filesystem_safe":
        server = filesystem_safe.make_server(Path(args.root), auth=auth, bucket=bucket)
    elif args.server == "web_fetch":
        server = web_fetch.make_server(auth=auth, bucket=bucket)
    else:
        server = sqlite_query.make_server(Path(args.db), auth=auth, bucket=bucket)
    server.serve_stdio()
    return 0


if __name__ == "__main__":
    sys.exit(main())
