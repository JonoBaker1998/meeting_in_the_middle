import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.main import client_key, create_app

B = {"city": "munich", "modes": ["transit"] * 3, "kind": "food", "prefs": [], "radius_m": 800}
PAGES = "https://jonobaker1998.github.io"


def test_search_rate_limited_at_30_per_minute():
    c = TestClient(create_app())
    codes = [c.post("/api/search", json=B).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429
    assert c.post("/api/search", json=B).json() == {"detail": "Too many requests — please slow down."}


def test_other_endpoints_limited_at_60_per_minute():
    c = TestClient(create_app())
    codes = [c.get("/api/heat", params={"city": "sf"}).status_code for _ in range(61)]
    assert codes[:60] == [200] * 60 and codes[60] == 429


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_rate_limit_is_per_client():
    app = create_app()

    def client(ip):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 1000)), base_url="http://t")

    async with client("1.1.1.1") as a, client("2.2.2.2") as b:
        for _ in range(30):
            await a.post("/api/search", json=B)
        assert (await a.post("/api/search", json=B)).status_code == 429
        assert (await b.post("/api/search", json=B)).status_code == 200


def test_rate_limit_key_is_connection_ip_not_raw_header():
    # On Render, uvicorn --proxy-headers turns X-Forwarded-For into request.client.host.
    # The key must use that, never a raw header a visitor could fake.
    class R:
        client = type("C", (), {"host": "9.9.9.9"})()
        headers = {"x-forwarded-for": "6.6.6.6"}

    assert client_key(R()) == "9.9.9.9"


def test_body_too_large():
    c = TestClient(create_app())
    big = dict(B, prefs=["x" * 20000])
    assert c.post("/api/search", json=big).status_code == 413


def test_cors_allows_pages_origin_only():
    c = TestClient(create_app())
    ok = c.options("/api/search", headers={"Origin": PAGES, "Access-Control-Request-Method": "POST"})
    bad = c.options("/api/search", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == PAGES
    assert "access-control-allow-origin" not in bad.headers


def test_limits_configurable_by_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_SEARCH", "2/minute")
    c = TestClient(create_app())
    assert [c.post("/api/search", json=B).status_code for _ in range(3)] == [200, 200, 429]
