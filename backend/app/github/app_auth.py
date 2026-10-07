import httpx
import jwt

# Exactly the GitHub App permissions DiffMate needs; tokens are requested with no more than this.
TOKEN_PERMISSIONS = {"metadata": "read", "contents": "read", "pull_requests": "write"}


def make_app_jwt(app_id: int, private_key_pem: str, now: int) -> str:
    """Short-lived JWT that authenticates as the GitHub App (GitHub allows at most 10 min)."""
    # iat is backdated 60 s to allow for clock drift
    claims = {"iat": now - 60, "exp": now + 540, "iss": str(app_id)}
    return jwt.encode(claims, private_key_pem, algorithm="RS256")


async def get_installation_token(
    http: httpx.AsyncClient, app_jwt: str, installation_id: int, repo_name: str
) -> str:
    """Exchange the App JWT for a 1-hour installation token limited to one repo."""
    r = await http.post(
        f"/app/installations/{installation_id}/access_tokens",
        headers={"Authorization": f"Bearer {app_jwt}"},
        json={"repositories": [repo_name], "permissions": TOKEN_PERMISSIONS},
    )
    r.raise_for_status()
    return r.json()["token"]
