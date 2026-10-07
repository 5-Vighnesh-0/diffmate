from functools import lru_cache

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

    webhook_max_body_bytes: int = 1_048_576  # 1 MiB; PR event payloads are far smaller
    delivery_ttl_seconds: int = 7 * 24 * 3600  # how long a delivery ID counts as seen


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
