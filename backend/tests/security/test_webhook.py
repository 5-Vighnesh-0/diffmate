import hashlib
import hmac
import json

import pytest

from app.api.webhooks import get_redis

SECRET = b"test-webhook-secret"  # matches conftest
SHA = "a" * 40
PR_OPENED = {
    "action": "opened",
    "number": 7,
    "pull_request": {"head": {"sha": SHA}},
    "repository": {"full_name": "o/r", "private": False},
    "installation": {"id": 42},
}
JOB_ID = f"review:o/r:7:{SHA}"


class FakeArq:
    """In-memory stand-in for the arq pool: SET NX, DELETE, and enqueue with job-ID dedupe."""

    def __init__(self):
        self.keys: dict[str, str] = {}
        self.jobs: dict[str, tuple] = {}
        self.fail_enqueue = False

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True

    async def delete(self, key):
        self.keys.pop(key, None)

    async def incr(self, key):  # rate-limit counter
        self.keys[key] = str(int(self.keys.get(key, "0")) + 1)
        return int(self.keys[key])

    async def expire(self, key, seconds):
        pass

    async def enqueue_job(self, function, *args, _job_id=None, **kwargs):
        if self.fail_enqueue:
            raise ConnectionError("redis down")
        if _job_id in self.jobs:
            return None
        self.jobs[_job_id] = (function, args)
        return object()


@pytest.fixture
def arq(app):
    fake = FakeArq()
    app.dependency_overrides[get_redis] = lambda: fake
    return fake


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()


async def send(client, payload=PR_OPENED, *, event="pull_request", delivery="d-1", signature=None):
    body = json.dumps(payload).encode()
    headers = {
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "X-Hub-Signature-256": signature if signature is not None else sign(body),
        "Content-Type": "application/json",
    }
    return await client.post("/webhooks/github", content=body, headers=headers)


async def test_valid_pr_opened_enqueues_one_review_job(client, arq):
    r = await send(client)

    assert r.status_code == 202
    assert arq.jobs == {JOB_ID: ("review_pr", ("o/r", 7, SHA, 42))}


async def test_private_repository_is_ignored_and_not_queued(client, arq):
    private = {**PR_OPENED, "repository": {"full_name": "o/r", "private": True}}

    r = await send(client, private)

    assert (r.status_code, r.json()) == (200, {"status": "ignored"})
    assert arq.jobs == {}


async def test_bad_signature_gets_401_and_no_job(client, arq):
    r = await send(client, signature="sha256=" + "0" * 64)

    assert r.status_code == 401
    assert arq.jobs == {}


async def test_missing_signature_gets_401(client, arq):
    r = await send(client, signature="")

    assert r.status_code == 401
    assert arq.jobs == {}


async def test_replayed_delivery_is_ignored(client, arq):
    first = await send(client, delivery="same")
    second = await send(client, delivery="same")

    assert first.status_code == 202
    assert second.status_code == 200
    assert len(arq.jobs) == 1


async def test_bad_signature_does_not_burn_the_delivery_id(client, arq):
    await send(client, delivery="d-9", signature="sha256=" + "0" * 64)
    r = await send(client, delivery="d-9")

    assert r.status_code == 202


async def test_oversized_body_gets_413(client, arq):
    big = b"x" * (1_048_576 + 1)
    r = await client.post(
        "/webhooks/github",
        content=big,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "d-1",
            "X-Hub-Signature-256": sign(big),
        },
    )

    assert r.status_code == 413
    assert arq.jobs == {}


async def test_oversized_chunked_body_without_length_gets_413(client, arq):
    async def chunks():
        for _ in range(2):
            yield b"x" * 600_000

    r = await client.post(
        "/webhooks/github",
        content=chunks(),
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "d-1",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
        },
    )

    assert r.status_code == 413


async def test_non_pr_event_is_ignored(client, arq):
    r = await send(client, {"zen": "hi"}, event="push")

    assert r.status_code == 200
    assert arq.jobs == {}


async def test_closed_pr_is_ignored(client, arq):
    r = await send(client, {**PR_OPENED, "action": "closed"})

    assert r.status_code == 200
    assert arq.jobs == {}


async def test_enqueue_failure_returns_503_and_releases_delivery_id(client, arq):
    arq.fail_enqueue = True
    failed = await send(client, delivery="d-5")
    arq.fail_enqueue = False
    retried = await send(client, delivery="d-5")

    assert failed.status_code == 503
    assert retried.status_code == 202


async def test_same_signed_body_with_a_new_delivery_id_is_ignored(client, arq):
    first = await send(client, delivery="d-a")
    replay = await send(client, delivery="d-b")

    assert first.status_code == 202
    assert replay.status_code == 200
    assert len(arq.jobs) == 1


@pytest.mark.parametrize(
    "field, value",
    [
        ("repository", {"full_name": "a/../../app/installations"}),
        ("repository", {"full_name": "no-slash"}),
        ("pull_request", {"head": {"sha": "not-a-sha"}}),
    ],
)
async def test_suspicious_repo_or_sha_gets_400_and_no_job(client, arq, field, value):
    r = await send(client, {**PR_OPENED, field: value})

    assert r.status_code == 400
    assert arq.jobs == {}


async def test_delivery_key_expires_after_seven_days(client, arq):
    seen = {}
    original = arq.set

    async def recording_set(key, value, nx=False, ex=None):
        seen["ex"] = ex
        return await original(key, value, nx=nx, ex=ex)

    arq.set = recording_set
    await send(client)

    assert seen["ex"] == 7 * 24 * 3600


async def test_new_event_for_an_already_queued_commit_reports_duplicate(client, arq):
    await send(client, delivery="d-1")
    r = await send(client, {**PR_OPENED, "action": "reopened"}, delivery="d-2")

    assert r.status_code == 200
    assert r.json() == {"status": "duplicate"}
    assert len(arq.jobs) == 1


async def test_missing_delivery_header_gets_400(client, arq):
    body = json.dumps(PR_OPENED).encode()
    r = await client.post(
        "/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": sign(body)},
    )

    assert r.status_code == 400
    assert arq.jobs == {}


@pytest.mark.parametrize("payload", [[1, 2], {"action": "opened"}])
async def test_non_object_or_incomplete_payload_gets_400(client, arq, payload):
    r = await send(client, payload)

    assert r.status_code == 400
    assert arq.jobs == {}


def reply_payload(
    association="MEMBER", user_id=5, user_type="User", in_reply_to=100, private=False
):
    return {
        "action": "created",
        "comment": {
            "id": 300,
            "in_reply_to_id": in_reply_to,
            "body": "this is fine",
            "diff_hunk": "@@ -1 +1 @@",
            "author_association": association,
            "user": {"id": user_id, "type": user_type},
        },
        "pull_request": {"number": 7, "user": {"id": 1}},
        "repository": {"full_name": "o/r", "private": private},
        "installation": {"id": 42},
    }


async def test_a_member_reply_to_a_review_comment_queues_one_answer(client, arq):
    r = await send(client, reply_payload(), event="pull_request_review_comment")

    assert r.status_code == 202
    assert arq.jobs == {
        "reply:o/r:300": ("answer_reply", ("o/r", 7, 42, 100, "this is fine", "@@ -1 +1 @@", 5))
    }


async def test_the_pr_author_may_reply_even_without_a_repo_role(client, arq):
    r = await send(client, reply_payload("NONE", user_id=1), event="pull_request_review_comment")

    assert r.status_code == 202


@pytest.mark.parametrize(
    "payload",
    [
        reply_payload("NONE"),  # a stranger on a public repo
        reply_payload(user_type="Bot"),  # DiffMate itself
        reply_payload(in_reply_to=None),  # a new comment, not a reply
        reply_payload(private=True),
    ],
)
async def test_other_review_comments_are_ignored(client, arq, payload):
    r = await send(client, payload, event="pull_request_review_comment")

    assert r.json() == {"status": "ignored"}
    assert arq.jobs == {}
