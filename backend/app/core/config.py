from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config comes from env vars (names in .env.example). No secret has a real default."""

    model_config = SettingsConfigDict(env_file="../.env", env_ignore_empty=True, extra="ignore")

    database_url: str
    redis_url: str
    # Only the API needs it. Empty means every webhook is rejected (verify_signature refuses it).
    github_webhook_secret: SecretStr = SecretStr("")
    github_app_id: int | None = None
    github_app_private_key_path: str | None = None
    github_app_private_key: SecretStr = SecretStr("")  # hosted: the PEM itself, from a secret

    # LLM (ADR 0003). The key comes from a project with no billing account; cap 0 = no LLM calls.
    llm_provider: str = "gemini"
    llm_model: str = "gemini-3.8-flash"
    gemini_api_key: SecretStr = SecretStr("")
    llm_daily_request_cap: int = 0
    llm_requests_per_minute: int = 4  # Gemini 3.8 Flash free tier allows 5 RPM
    llm_thinking_level: str = "low"  # minimal | low | high
    llm_timeout_seconds: float = 90

    agent_max_steps: int = 8
    agent_max_tokens: int = 60_000
    confidence_threshold: float = 0.7
    strict_confidence_threshold: float = 0.9  # categories a repo voted mostly Not useful
    comment_cap: int = 5

    # Dashboard login (GitHub App user OAuth). Secret only in the API container.
    github_oauth_client_id: str = ""
    github_oauth_client_secret: SecretStr = SecretStr("")
    public_api_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:5173"
    frontend_dist: str = ""  # hosted: the built frontend, served from the API's own origin
    client_ip_header: str = "cf-connecting-ip"  # set by Cloudflare (tunnel); "" = direct peer

    webhook_max_body_bytes: int = 1_048_576  # 1 MiB; PR event payloads are far smaller
    delivery_ttl_seconds: int = 7 * 24 * 3600  # how long a delivery ID counts as seen

    def github_app_key(self) -> str:
        """The App's private key: from the secret setting (hosting) or the key file (laptop)."""
        if key := self.github_app_private_key.get_secret_value():
            return key.replace("\\n", "\n")  # dashboards often store a PEM on one line
        if self.github_app_private_key_path:
            return Path(self.github_app_private_key_path).read_text()
        raise RuntimeError("Set GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
