"""Server-side sessions in Redis. The browser only holds a random ID in an HttpOnly cookie;
no GitHub token is ever stored."""

import json
import secrets
from dataclasses import asdict, dataclass

SESSION_COOKIE = "diffmate_session"
SESSION_TTL_SECONDS = 8 * 3600


@dataclass
class Session:
    user_id: int
    login: str
    installation_ids: list[int]
    repo_ids: list[int]  # repos this user can access inside those installations
    csrf: str


async def create_session(
    redis, user_id: int, login: str, installation_ids: list[int], repo_ids: list[int]
):
    sid = secrets.token_urlsafe(32)
    session = Session(user_id, login, installation_ids, repo_ids, secrets.token_urlsafe(32))
    await redis.set(f"session:{sid}", json.dumps(asdict(session)), ex=SESSION_TTL_SECONDS)
    return sid, session


async def load_session(redis, sid: str) -> Session | None:
    if not sid or len(sid) > 100:
        return None
    raw = await redis.get(f"session:{sid}")
    return Session(**json.loads(raw)) if raw else None


async def delete_session(redis, sid: str) -> None:
    if sid:
        await redis.delete(f"session:{sid}")
