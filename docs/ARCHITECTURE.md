# Architecture

## Shared core (`mcp_server_suite`)
- `protocol.McpServer` — minimal JSON-RPC: initialize / ping / tools/list / tools/call.
- `auth.AuthValidator` — bearer token from `MCP_AUTH_TOKEN`, constant-time compare.
- `rate_limit.TokenBucket` — burst + sustained limits, injectable clock for tests.
- `errors` — structured errors mapped to JSON-RPC error codes.

## Servers
| Server | Tools | Guardrails |
|---|---|---|
| filesystem_safe | list_dir, read_file | cwd jail, 64KB read cap |
| web_fetch | fetch | domain allowlist, response cache |
| sqlite_query | query | SELECT/WITH only, single statement, `mode=ro`, 500-row cap |

See `docs/INSTALL.md` and each `servers/<name>/README.md`.
