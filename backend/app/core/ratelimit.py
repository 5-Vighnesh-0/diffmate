"""Fixed-window rate limit per client IP and minute, counted in Redis (shared by all workers)."""

import time

from fastapi import Depends, HTTPException, Request

from app.api.deps import get_redis
from app.core.config import get_settings

now = time.time  # replaced in tests to keep the window fixed


def client_ip(request: Request) -> str:
    # Only the tunnel or a 127.0.0.1-bound port reach the API, so the proxy header is trusted.
    header = get_settings().client_ip_header
    forwarded = request.headers.get(header, "") if header else ""
    return forwarded.strip()[:64] or (request.client.host if request.client else "unknown")


def rate_limit(bucket: str, per_minute: int):
    async def check(request: Request, redis=Depends(get_redis)) -> None:
        t = now()
        key = f"rl:{bucket}:{client_ip(request)}:{int(t // 60)}"
        await redis.set(key, 0, nx=True, ex=120)  # TTL exists before the first increment
        count = await redis.incr(key)
        if count > per_minute:
            retry_after = str(int(60 - t % 60) + 1)
            raise HTTPException(429, "Too many requests", headers={"Retry-After": retry_after})

    return check
