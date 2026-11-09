"""Benchmark: request throughput + rate-limit behaviour.

Run: python benchmarks/bench.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_server_suite.rate_limit import TokenBucket
from mcp_server_suite.servers_impl import filesystem_safe


def main() -> int:
    """Measure in-process JSON-RPC throughput and limiter correctness."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "f.txt").write_text("benchmark payload")
        server = filesystem_safe.make_server(root)
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "read_file", "arguments": {"path": "f.txt"}}}
        n = 1000
        start = time.perf_counter()
        for _ in range(n):
            server.handle(req)
        elapsed = time.perf_counter() - start
        rps = n / elapsed
        bucket = TokenBucket(capacity=5, refill_per_s=0.0, clock=lambda: 0.0)
        allowed = sum(int(bucket.allow()) for _ in range(20))
    print(f"requests: {n} elapsed_s: {elapsed:.3f}")
    print(f"requests_per_sec: {rps:.0f}")
    print(f"rate_limit: allowed {allowed}/20 with capacity 5 (expected 5)")
    print("target: 500+ installs or one real adopting team; throughput is a local proxy.")
    return 0 if rps > 100 and allowed == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
