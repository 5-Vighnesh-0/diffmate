import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

# Public paid-tier list prices, USD per million tokens (checked 2026-10-06). We pay $0 on the
# free tier; these only produce the clearly labelled *estimated* cost per PR.
LIST_PRICE_PER_MILLION = {"gemini-3.8-flash": (0.75, 3.75)}


def estimated_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = LIST_PRICE_PER_MILLION.get(model, (0.0, 0.0))
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


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
    """Free-tier guard shared by all runs: at most `cap` LLM requests per UTC day, and at most
    `per_minute` per clock minute (extra calls wait for the next minute). 0 = no minute limit."""

    def __init__(self, redis, cap: int, per_minute: int = 0, clock=time.time, sleep=asyncio.sleep):
        self.redis, self.cap, self.per_minute = redis, cap, per_minute
        self.clock, self.sleep = clock, sleep

    async def take(self) -> bool:
        key = f"llm:requests:{datetime.now(UTC):%Y-%m-%d}"
        used = await self.redis.incr(key)
        if used == 1:
            await self.redis.expire(key, 2 * 24 * 3600)
        if used > self.cap:
            return False
        while self.per_minute:
            now = self.clock()
            minute_key = f"llm:minute:{int(now // 60)}"
            in_minute = await self.redis.incr(minute_key)
            if in_minute == 1:
                await self.redis.expire(minute_key, 120)
            if in_minute <= self.per_minute:
                break
            await self.sleep(60 - now % 60 + 0.5)  # wait for the next minute
        return True
