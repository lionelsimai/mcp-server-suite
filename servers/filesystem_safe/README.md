# filesystem_safe

Jailed, read-only filesystem access. Tools: `list_dir`, `read_file` (64KB cap).
Run: `mcp-suite serve filesystem_safe --root /data/jail`
Auth: set `MCP_AUTH_TOKEN`; clients pass it as `_meta.token`.
