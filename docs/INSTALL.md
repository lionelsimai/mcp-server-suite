# Install

```bash
pip install -e .
export MCP_AUTH_TOKEN="your-secret-token"   # clients send it as _meta.token
mcp-suite serve filesystem_safe --root /data/jail
mcp-suite serve web_fetch                            # default allowlist: example.com, example.org
mcp-suite serve web_fetch --allowlist example.net    # custom domains (repeatable)
mcp-suite serve sqlite_query --db app.db
```

Auth is **fail-closed**: if `MCP_AUTH_TOKEN` is unset, `serve` refuses
to start. For local development only, pass `--allow-unauthenticated`
(the server prints a stderr warning in that mode).

Each server can also be started directly from a checkout, e.g.
`python servers/filesystem_safe/server.py --root /data/jail` — those
entrypoints delegate to the same CLI and the same auth policy.

Protocol: newline-delimited JSON-RPC 2.0 on stdio — `initialize`, `ping`,
`tools/list`, `tools/call`. Notifications (e.g.
`notifications/initialized`) are accepted silently, per spec. No
external MCP SDK required.

## MCP client configuration

Claude Desktop (`claude_desktop_config.json`) or any client using the
`mcp.json` convention:

```json
{
  "mcpServers": {
    "filesystem_safe": {
      "command": "mcp-suite",
      "args": ["serve", "filesystem_safe", "--root", "/data/jail"],
      "env": { "MCP_AUTH_TOKEN": "your-secret-token" }
    },
    "web_fetch": {
      "command": "mcp-suite",
      "args": ["serve", "web_fetch", "--allowlist", "example.com"],
      "env": { "MCP_AUTH_TOKEN": "your-secret-token" }
    },
    "sqlite_query": {
      "command": "mcp-suite",
      "args": ["serve", "sqlite_query", "--db", "/data/app.db"],
      "env": { "MCP_AUTH_TOKEN": "your-secret-token" }
    }
  }
}
```

Note: this minimal implementation takes the bearer token from each
request's `_meta.token` field rather than a transport-level header;
clients must be configured (or adapted) to send it that way.
