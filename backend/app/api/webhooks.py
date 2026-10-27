import json
import logging
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.deps import get_redis
from app.core.config import Settings, get_settings
from app.core.security import verify_signature
from app.queue.jobs import enqueue_review

router = APIRouter()
log = logging.getLogger(__name__)

REVIEW_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}
REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


async def read_limited(request: Request, limit: int) -> bytes | None:
    """Read the body, giving up (None) once it passes `limit`, even if Content-Length lies."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            return None
    return bytes(body)


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    redis=Depends(get_redis),
):
    body = await read_limited(request, settings.webhook_max_body_bytes)
    if body is None:
        return error(413, "too_large", "Body too large")

    secret = settings.github_webhook_secret.get_secret_value().encode()
    if not verify_signature(secret, body, request.headers.get("x-hub-signature-256")):
        return error(401, "bad_signature", "Invalid signature")

    delivery = request.headers.get("x-github-delivery")
    if not delivery:
        return error(400, "no_delivery_id", "Missing X-GitHub-Delivery")
    # Replay key = the signature, not X-GitHub-Delivery: the delivery header is not signed,
    # so a captured body resent under a new delivery ID must still count as seen.
    # Checked only after the signature, so unsigned requests cannot fill this set.
    key = f"webhook:{request.headers['x-hub-signature-256']}"
    if not await redis.set(key, "1", nx=True, ex=settings.delivery_ttl_seconds):
        log.info("duplicate delivery %s ignored", delivery)
        return JSONResponse({"status": "duplicate"}, status_code=200)

    event = request.headers.get("x-github-event")
    try:
        payload = json.loads(body)
        action = payload.get("action")
    except (ValueError, AttributeError):
        return error(400, "bad_json", "Body is not a JSON object")
    if event != "pull_request" or action not in REVIEW_ACTIONS:
        return JSONResponse({"status": "ignored"}, status_code=200)

    try:
        repo = payload["repository"]["full_name"]
        pr = int(payload["number"])
        sha = payload["pull_request"]["head"]["sha"]
        installation_id = int(payload["installation"]["id"])
    except (KeyError, TypeError, ValueError):
        return error(400, "bad_payload", "Missing pull request fields")
    # These go into GitHub API paths; reject anything that is not a plain owner/name and SHA.
    if not REPO_NAME.fullmatch(repo) or not COMMIT_SHA.fullmatch(sha):
        return error(400, "bad_payload", "Unexpected repository name or commit SHA")
    # Public code only: the free AI tier may learn from what it reads. Missing flag = private.
    if payload["repository"].get("private") is not False:
        log.info("private repository %s ignored (delivery %s)", repo, delivery)
        return JSONResponse({"status": "ignored"}, status_code=200)

    try:
        queued = await enqueue_review(
            redis, repo=repo, pr=pr, sha=sha, installation_id=installation_id
        )
    except Exception:
        # Forget the delivery so GitHub's redelivery can succeed later.
        await redis.delete(key)
        log.exception("enqueue failed for delivery %s", delivery)
        return error(503, "queue_unavailable", "Try again later")

    if not queued:
        log.info("commit %s#%s@%s already queued (delivery %s)", repo, pr, sha[:7], delivery)
        return JSONResponse({"status": "duplicate"}, status_code=200)
    log.info("queued review %s#%s@%s (delivery %s)", repo, pr, sha[:7], delivery)
    return JSONResponse({"status": "queued"}, status_code=202)
