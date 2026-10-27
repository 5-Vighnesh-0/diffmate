import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

router = APIRouter()

CHECK_TIMEOUT_SECONDS = 2.0  # a stalled Redis must fail the check, not hang /health


async def _check(probe, *args) -> bool:
    try:
        return bool(await asyncio.wait_for(probe(*args), CHECK_TIMEOUT_SECONDS))
    except Exception:
        return False


# No Postgres probe: /health is public, and each probe would wake the Neon database and use
# its free compute hours. start.sh runs migrations before the API, so a running API had a DB.
async def health_checks(request: Request) -> dict[str, bool]:
    state = request.app.state
    return {
        "redis": await _check(state.redis.ping),
    }


@router.get("/health")
async def health(checks: dict[str, bool] = Depends(health_checks)):
    if all(checks.values()):
        return {"status": "ok"}
    return JSONResponse({"status": "degraded", "checks": checks}, status_code=503)
