import hashlib
import hmac


def verify_signature(secret: bytes, body: bytes, header: str | None) -> bool:
    """Check GitHub's X-Hub-Signature-256 header with a constant-time compare."""
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    # Compare bytes: str compare_digest raises TypeError on non-ASCII input.
    return hmac.compare_digest(expected.encode(), header.encode())
