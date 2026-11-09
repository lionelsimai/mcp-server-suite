# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-11-09

World-class remediation after an adversarial audit (was scored 5/10, FIX).

### Protocol correctness
- Every tool now advertises a real `inputSchema` (properties, types,
  `required`) — 0.1.0 shipped empty schemas, so clients could not
  discover argument shapes.
- Notifications (no `id`, incl. `notifications/initialized`) receive
  NO response, per JSON-RPC/MCP.
- A malformed JSON line returns -32700 and `serve_stdio` survives to
  serve the next line (was: one bad line crashed the server).
- Tool handler exceptions return a result with `isError: true` and a
  generic message; internal exception text no longer leaks.

### Security
- Filesystem jail uses `Path.is_relative_to` (sibling-prefix escape
  fixed); file reads stream with a hard 64KB cap instead of
  read-whole-then-truncate.
- web_fetch re-validates EVERY redirect hop against the allowlist
  (urllib auto-redirects disabled) and rejects non-http(s) schemes.
- sqlite_query executes each statement exactly once (was: twice) and
  blocks table-valued `pragma_*()` functions.
- Auth fails closed: `serve` refuses to start with `MCP_AUTH_TOKEN`
  unset unless `--allow-unauthenticated` is passed explicitly.

### Added
- `--allowlist` CLI flag (repeatable) for web_fetch domains.
- `servers/*/server.py` are now real entrypoints delegating to the
  CLI (were docstring stubs).
- MCP client configuration example (Claude Desktop / `mcp.json`) in
  docs/INSTALL.md.
- tests/test_remediation.py with one test per fix. Four pre-existing
  assertions were updated from protocol-`error` to result-`isError`
  semantics, and the demo's write-blocked line changed accordingly.

## [0.1.0] - 2026-11-09

### Added
- Initial public release: core engine, CLI, offline demo, tests, benchmarks, CI.
