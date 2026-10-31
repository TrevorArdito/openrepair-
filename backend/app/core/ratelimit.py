"""Tiny in-memory rate limiter (per process). Good enough for one small server;
swap for a shared store if we ever run several app servers.

Keys are hashed so we don't keep raw IP addresses around."""

import hashlib
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import AppError

_hits: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def client_key(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def rate_limit(bucket: str, limit: int, window_seconds: int):
    def _dep(request: Request) -> None:
        key = f"{bucket}:{client_key(request)}"
        now = time.monotonic()
        q = _hits[key]
        while q and q[0] <= now - window_seconds:
            q.popleft()
        if len(q) >= limit:
            raise AppError("rate_limited", 429, retry_after=window_seconds)
        q.append(now)

    return _dep
