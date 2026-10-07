from app.core.config import get_settings


def test_tests_never_read_the_real_env_file():
    # conftest sets only fake values; anything from ../.env (real secrets) must not leak in
    assert get_settings().github_app_id is None
    assert get_settings().github_webhook_secret.get_secret_value() == "test-webhook-secret"
