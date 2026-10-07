import hashlib
import hmac

from app.core.security import verify_signature

SECRET = b"s3cret"
BODY = b'{"action":"opened"}'


def sign(body: bytes, secret: bytes = SECRET) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted():
    assert verify_signature(SECRET, BODY, sign(BODY))


def test_signature_made_with_another_secret_is_rejected():
    assert not verify_signature(SECRET, BODY, sign(BODY, b"other"))


def test_missing_signature_is_rejected():
    assert not verify_signature(SECRET, BODY, None)


def test_sha1_style_header_is_rejected():
    digest = hmac.new(SECRET, BODY, hashlib.sha256).hexdigest()
    assert not verify_signature(SECRET, BODY, "sha1=" + digest)


def test_tampered_body_is_rejected():
    assert not verify_signature(SECRET, BODY + b" ", sign(BODY))


def test_empty_secret_never_verifies():
    assert not verify_signature(b"", BODY, sign(BODY, b""))


def test_non_ascii_header_is_rejected_not_crashing():
    assert not verify_signature(SECRET, BODY, "sha256=\xff" + "0" * 63)
