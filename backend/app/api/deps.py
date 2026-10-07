"""Shared request dependencies: Redis, DB session, outbound HTTP client, login session, CSRF."""

import hmac

from fastapi import Depends, HTTPException, Request

from app.core.sessions import SESSION_COOKIE, Session, load_session


def get_redis(request: Request):
    return request.app.state.redis


def get_http(request: Request):
    return request.app.state.http


async def get_db(request: Request):
    async with request.app.state.sessionmaker() as s:
        yield s


async def get_session(request: Request, redis=Depends(get_redis)) -> Session:
    session = await load_session(redis, request.cookies.get(SESSION_COOKIE, ""))
    if session is None:
        raise HTTPException(401, "Not signed in")
    return session


async def require_csrf(request: Request, session: Session = Depends(get_session)) -> Session:
    """State-changing requests must echo the session's CSRF token in X-CSRF-Token."""
    token = request.headers.get("x-csrf-token", "")
    if not hmac.compare_digest(token.encode(), session.csrf.encode()):
        raise HTTPException(403, "Missing or wrong CSRF token")
    return session
