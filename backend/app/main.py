import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.api import auth, findings, health, runs, webhooks
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.ratelimit import rate_limit
from app.db.session import make_engine, make_sessionmaker

log = logging.getLogger(__name__)

SECURITY_HEADERS = {
    # The API only serves JSON: nothing may load, frame, or sniff it.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",  # honoured on HTTPS only
}
# The built frontend's pages: code, styles, fonts and API calls from this origin only.
PAGE_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.db = make_engine(settings.database_url)
    app.state.sessionmaker = make_sessionmaker(app.state.db)
    # One arq pool serves as the job queue and as the plain Redis client.
    app.state.redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    app.state.http = httpx.AsyncClient(timeout=10.0)  # GitHub OAuth and user lookups
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    await app.state.db.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DiffMate", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = PAGE_CSP
        return response

    def error(status: int, message: str, headers=None) -> JSONResponse:
        # One error shape everywhere (docs/api.md); never internals or echoed input.
        code = HTTPStatus(status).phrase.lower().replace(" ", "_").replace("-", "_")
        body = {"error": {"code": code, "message": message}}
        return JSONResponse(body, status_code=status, headers=headers)

    @app.exception_handler(HTTPException)  # Starlette's: also covers 404/405 from routing
    async def http_error(request: Request, exc: HTTPException):
        return error(exc.status_code, str(exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return error(422, "Invalid request")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("unhandled error on %s", request.url.path)
        return error(500, "Internal error")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    dashboard_limit = [Depends(rate_limit("dashboard", 60))]
    app.include_router(health.router, dependencies=[Depends(rate_limit("health", 30))])
    app.include_router(webhooks.router, dependencies=[Depends(rate_limit("webhook", 120))])
    app.include_router(auth.router, dependencies=dashboard_limit)
    app.include_router(runs.router, dependencies=dashboard_limit)
    app.include_router(findings.router, dependencies=dashboard_limit)
    if settings.frontend_dist:
        serve_frontend(app, Path(settings.frontend_dist))
    return app


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Hosted: one origin for the app and the API, so the session cookie stays first-party."""
    index = dist / "index.html"
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    async def page() -> FileResponse:
        return FileResponse(index, media_type="text/html")

    # Only the frontend's own routes; anything else stays a JSON 404. HEAD too: uptime monitors
    # check with HEAD by default, and a 405 there reads as "site down".
    for path in ("/", "/dashboard", "/dashboard/runs/{run_id:int}"):
        app.add_api_route(path, page, methods=["GET", "HEAD"], include_in_schema=False)


app = create_app()
