# Install

```bash
pip install -e .
export MCP_AUTH_TOKEN="your-secret-token"   # clients send it as _meta.token
mcp-suite serve filesystem_safe --root /data/jail
mcp-suite serve web_fetch
mcp-suite serve sqlite_query --db app.db
```

Protocol: newline-delimited JSON-RPC 2.0 on stdio — `initialize`, `ping`,
`tools/list`, `tools/call`. No external MCP SDK required.
