import json

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.github.app_auth import get_installation_token, make_app_jwt

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()


def test_app_jwt_is_rs256_with_short_expiry_and_app_issuer():
    token = make_app_jwt(123, PEM, now=1_000_000)

    claims = jwt.decode(
        token, KEY.public_key(), algorithms=["RS256"], options={"verify_exp": False}
    )

    assert claims == {"iat": 999_940, "exp": 1_000_540, "iss": "123"}


async def test_installation_token_is_scoped_to_one_repo_and_minimum_permissions():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"token": "inst-token"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.github.com"
    ) as http:
        token = await get_installation_token(http, "app-jwt", 42, "r")

    assert token == "inst-token"
    assert seen == {
        "path": "/app/installations/42/access_tokens",
        "auth": "Bearer app-jwt",
        "body": {
            "repositories": ["r"],
            "permissions": {"metadata": "read", "contents": "read", "pull_requests": "write"},
        },
    }
