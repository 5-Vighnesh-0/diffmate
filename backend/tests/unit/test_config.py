from app.core.config import get_settings


def test_tests_never_read_the_real_env_file():
    # conftest sets only fake values; anything from ../.env (real secrets) must not leak in
    assert get_settings().github_app_id is None
    assert get_settings().github_webhook_secret.get_secret_value() == "test-webhook-secret"


def test_app_key_comes_from_a_secret_setting_or_a_file(tmp_path):
    from app.core.config import Settings

    pem = "-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----\n"
    base = {"database_url": "x", "redis_url": "y"}

    # Hosting dashboards often store a multi-line secret with literal "\n".
    one_line = pem.replace("\n", "\\n")
    assert Settings(**base, github_app_private_key=one_line).github_app_key() == pem

    path = tmp_path / "key.pem"
    path.write_text(pem)
    assert Settings(**base, github_app_private_key_path=str(path)).github_app_key() == pem

    import pytest

    with pytest.raises(RuntimeError, match="GITHUB_APP_PRIVATE_KEY"):
        Settings(**base).github_app_key()
