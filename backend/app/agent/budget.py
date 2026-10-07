import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

# Public paid-tier list prices, USD per million tokens (checked 2026-10-06). We pay $0 on the
# free tier; these only produce the clearly labelled *estimated* cost per PR.
LIST_PRICE_PER_MILLION = {"gemini-3.8-flash": (0.75, 3.75)}


def estimated_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = LIST_PRICE_PER_MILLION.get(model, (0.0, 0.0))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


GOOGLE_QUOTA_TZ = ZoneInfo("America/Los_Angeles")  # Gemini daily quotas reset at Pacific midnight


def daily_key(model: str) -> str:
    """One request counter per model and per Google quota day."""
    return f"llm:requests:{model}:{datetime.now(GOOGLE_QUOTA_TZ):%Y-%m-%d}"


@dataclass
class Budget:
    """Hard per-run caps. The loop checks these before every LLM call."""

    max_steps: int = 8
    max_tokens: int = 60_000
    steps: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    last_tokens_in: int = 0

    @property
    def tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    def charge(self, tokens_in: int, tokens_out: int) -> None:
        self.steps += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.last_tokens_in = tokens_in


class DailyCap:
    """Free-tier guard shared by all runs: at most `cap` requests per model and Google quota day
    (Pacific), and requests
    spaced 60/`per_minute` seconds apart (0 = no spacing). Even spacing keeps every rolling
    minute within the limit; counting per clock minute would allow bursts across a boundary.
    The spacing is exact for one worker process with max_jobs=1 (worker.py)."""

    def __init__(
        self,
        redis,
        cap: int,
        per_minute: int = 0,
        model: str = "default",
        clock=time.time,
        sleep=asyncio.sleep,
    ):
        self.redis, self.cap, self.per_minute, self.model = redis, cap, per_minute, model
        self.clock, self.sleep = clock, sleep

    async def take(self) -> bool:
        key = daily_key(self.model)
        await self.redis.set(key, 0, nx=True, ex=2 * 24 * 3600)  # TTL set before counting
        used = await self.redis.incr(key)
        if used > self.cap:
            return False
        if self.per_minute:
            last = float(await self.redis.get("llm:last_request_at") or 0)
            wait = last + 60 / self.per_minute - self.clock()
            if wait > 0:
                await self.sleep(wait)
            await self.redis.set("llm:last_request_at", str(self.clock()), ex=120)
        return True
