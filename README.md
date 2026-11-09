# MCP Server Suite

[![CI](https://github.com/lionelsimai/mcp-server-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/lionelsimai/mcp-server-suite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

**3 production MCP servers with auth, rate limits, docs.**

**Target:** 500+ installs or adopted by one real team.
**Shows:** You build plumbing others build on.

## Problem -> Solution
Every agent team re-builds the same unsafe tool servers. This suite ships
three hardened MCP servers — filesystem, web fetch, SQLite — over stdio
JSON-RPC with shared bearer auth, token-bucket rate limits and structured
errors, and **zero external SDK dependency** so it installs anywhere.

## Architecture
```mermaid
flowchart LR
  A[Agent / client] -->|JSON-RPC stdio| B[Auth gate]
  B --> C[Rate limiter]
  C --> D[filesystem_safe]
  C --> E[web_fetch]
  C --> F[sqlite_query]
```

## Quickstart (<2 min)
```bash
git clone https://github.com/lionelsimai/mcp-server-suite.git
cd mcp-server-suite
pip install -e .
mcp-suite demo
mcp-suite list
export MCP_AUTH_TOKEN="your-token"
mcp-suite serve filesystem_safe --root /data/jail
```

## Real demo output
```
filesystem_safe read: hello from filesystem_safe
web_fetch first: <html>fetched https://example.com/a</html>
web_fetch cached: <html>fetched https://example.com/a</html> (network calls: 1)
sqlite_query result: {"columns": ["name"], "rows": [["alpha"], ["beta"]]}
sqlite_query write blocked: only SELECT/WITH queries are allowed
auth check (wrong token): unauthorized: bad or missing token
```

## Servers
- **filesystem_safe** — jailed `list_dir` / `read_file`. [README](servers/filesystem_safe/README.md)
- **web_fetch** — allowlisted, cached `fetch`. [README](servers/web_fetch/README.md)
- **sqlite_query** — read-only `query`. [README](servers/sqlite_query/README.md)

Install details: [docs/INSTALL.md](docs/INSTALL.md).

## Benchmarks
```bash
python benchmarks/bench.py
```
Measures in-process requests/sec (1,000 calls) and verifies rate-limit
behaviour (capacity-5 bucket admits exactly 5 of 20 rapid calls).

## Limitations (honest)
- Minimal protocol subset (no streaming, resources or prompts yet).
- Auth is one shared bearer token, not per-client credentials / OAuth.
- Web fetch cache is in-memory and per-process.

## Roadmap
- [ ] Resources/prompts support, per-client tokens, persistent cache
- [ ] PyPI release, Docker images per server
- [ ] Conformance run against the official MCP inspector

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Licence: MIT — see [LICENSE](LICENSE).
