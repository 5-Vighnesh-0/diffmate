import httpx
import pytest

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
async def site(tmp_path, monkeypatch):
    """The app serving a tiny built frontend, as on the hosted deployment."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.parametrize("path", ["/", "/dashboard", "/dashboard/runs/5"])
async def test_app_pages_get_the_frontend_with_a_strict_page_csp(site, path):
    r = await site.get(path)

    assert r.status_code == 200
    assert "id=root" in r.text
    csp = r.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp


async def test_built_assets_are_served(site):
    r = await site.get("/assets/app.js")

    assert r.status_code == 200
    assert r.text == "console.log(1)"


async def test_api_responses_keep_the_json_only_csp(site):
    r = await site.get("/health/nope")

    assert r.headers["content-security-policy"].startswith("default-src 'none'")


@pytest.mark.parametrize("path", ["/dashboard/runs/x", "/admin", "/assets/../index.html"])
async def test_unknown_paths_are_not_the_app(site, path):
    r = await site.get(path)

    assert r.status_code == 404


async def test_without_a_build_only_the_api_is_served(client):
    assert (await client.get("/")).status_code == 404


async def test_uptime_monitors_using_head_see_the_pages_as_up(site):
    # UptimeRobot checks with HEAD by default; a 405 there reads as "down".
    r = await site.head("/")

    assert r.status_code == 200
    assert r.text == ""
