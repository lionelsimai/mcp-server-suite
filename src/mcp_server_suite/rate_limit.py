"""Token-bucket rate limiter."""

from __future__ import annotations

import time


class TokenBucket:
    """Classic token bucket: ``capacity`` burst, ``refill_per_s`` sustained."""

    def __init__(self, capacity: float = 20.0, refill_per_s: float = 5.0,
                 clock: object = time.monotonic) -> None:
        self.capacity = capacity
        self.refill_per_s = refill_per_s
        self._clock = clock  # type: ignore[assignment]
        self.tokens = capacity
        self._last = float(self._clock())  # type: ignore[operator]

    def allow(self, cost: float = 1.0) -> bool:
        """Consume tokens if available; return whether the call is allowed."""
        now = float(self._clock())  # type: ignore[operator]
        elapsed = max(0.0, now - self._last)
        self._last = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
