import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter()

CHECK_TIMEOUT_SECONDS = 2.0  # a stalled Postgres/Redis must fail the check, not hang /health


async def _postgres_ok(db) -> bool:
    async with db.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def _check(probe, *args) -> bool:
    try:
        return bool(await asyncio.wait_for(probe(*args), CHECK_TIMEOUT_SECONDS))
    except Exception:
        return False


async def health_checks(request: Request) -> dict[str, bool]:
    state = request.app.state
    return {
        "postgres": await _check(_postgres_ok, state.db),
        "redis": await _check(state.redis.ping),
    }


@router.get("/health")
async def health(checks: dict[str, bool] = Depends(health_checks)):
    if all(checks.values()):
        return {"status": "ok"}
    return JSONResponse({"status": "degraded", "checks": checks}, status_code=503)
