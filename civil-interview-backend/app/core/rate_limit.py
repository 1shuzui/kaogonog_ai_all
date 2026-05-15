from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import HTTPException, Request

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request | None) -> str:
    if not request:
        return "unknown"
    forwarded = str(request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request | None, scope: str, *, limit: int, window_seconds: int, identity: str = "") -> None:
    now = time()
    ip = client_ip(request)
    key = f"{scope}:{ip}:{identity or '-'}"
    bucket = _BUCKETS[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    bucket.append(now)
