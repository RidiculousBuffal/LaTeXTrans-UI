from __future__ import annotations

import threading
import time
import math
from collections import deque

from fastapi import HTTPException, Request, status

from backend.app.core.config import get_settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def enforce(self, *, request: Request, scope: str, limit: int, window_seconds: int) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return
        if limit <= 0 or window_seconds <= 0:
            return

        now = time.time()
        key = f"{scope}:{self._resolve_client_key(request)}"
        retry_after = window_seconds

        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, math.ceil(window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

    def _resolve_client_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        client = request.client
        if client and client.host:
            return client.host
        return "unknown"


rate_limiter = InMemoryRateLimiter()
