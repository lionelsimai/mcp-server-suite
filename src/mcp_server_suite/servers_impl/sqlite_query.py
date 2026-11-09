"""SQLite server: read-only queries only."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from mcp_server_suite.errors import PolicyError
from mcp_server_suite.protocol import McpServer, Tool

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|vacuum|attach|pragma)\b",
    re.IGNORECASE,
)
# Table-valued pragma functions (pragma_table_info(...) etc.) slip past
# \bpragma\b because "_" is a word character — block them explicitly.
PRAGMA_FUNCTION = re.compile(r"pragma_\w+\s*\(", re.IGNORECASE)

_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sql": {
            "type": "string",
            "description": "A single read-only SELECT or WITH statement",
        },
    },
    "required": ["sql"],
}


def assert_read_only(sql: str) -> str:
    """Validate that SQL is a single read-only SELECT/WITH statement."""
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        raise PolicyError("only a single statement is allowed")
    if not re.match(r"(?is)^\s*(select|with)\b", cleaned):
        raise PolicyError("only SELECT/WITH queries are allowed")
    if FORBIDDEN.search(cleaned):
        raise PolicyError("write/DDL keywords are forbidden")
    if PRAGMA_FUNCTION.search(cleaned):
        raise PolicyError("pragma functions are forbidden")
    return cleaned


def make_server(db_path: Path, auth: object = None, bucket: object = None) -> McpServer:
    """Build the sqlite_query server for an existing database file."""
    path = Path(db_path)

    def query(args: dict[str, Any]) -> Any:
        sql = assert_read_only(str(args.get("sql", "")))
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            # Execute exactly once: columns and rows come from the
            # same cursor (0.1.0 executed the statement twice).
            cursor = conn.execute(sql)
            cols = [d[0] for d in cursor.description or []]
            rows = cursor.fetchall()
        finally:
            conn.close()
        return {"columns": cols, "rows": [list(r) for r in rows[:500]]}

    return McpServer(
        "sqlite_query",
        [Tool("query", "Run a read-only SQL query", query, input_schema=_QUERY_SCHEMA)],
        auth=auth, bucket=bucket)
