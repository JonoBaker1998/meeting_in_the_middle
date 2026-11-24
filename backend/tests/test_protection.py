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


class _Req:
    def __init__(self, host, xff=None):
        self.client = type("C", (), {"host": host})()
        self.headers = {"x-forwarded-for": xff} if xff else {}


def test_rate_limit_key_ignores_forwarded_header_without_trusted_proxy(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    assert client_key(_Req("9.9.9.9", "6.6.6.6")) == "9.9.9.9"


def test_rate_limit_key_uses_entry_added_by_trusted_proxy(monkeypatch):
    # Render's proxy appends the real visitor IP to whatever the visitor sent.
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    assert client_key(_Req("10.0.0.1", "1.2.3.4, 203.0.113.7")) == "203.0.113.7"
    assert client_key(_Req("10.0.0.1", "203.0.113.7")) == "203.0.113.7"
    assert client_key(_Req("10.0.0.1")) == "10.0.0.1"


def test_spoofed_forwarded_header_cannot_dodge_rate_limit(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    c = TestClient(create_app())
    codes = [c.post("/api/search", json=B, headers={"X-Forwarded-For": f"6.6.6.{i}, 203.0.113.7"}).status_code
             for i in range(31)]
    assert codes[30] == 429


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


def test_render_chain_visitor_cloudflare_loadbalancer(monkeypatch):
    # Shape observed live on Render: "<visitor>, <cloudflare>, <render LB>"; the LB IP varies per request.
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "3")
    assert client_key(_Req("x", "203.0.113.7, 172.71.0.1, 10.27.0.5")) == "203.0.113.7"
    assert client_key(_Req("x", "203.0.113.7, 172.71.0.1, 10.28.0.9")) == "203.0.113.7"
    # a visitor-supplied X-Forwarded-For only adds entries on the left
    assert client_key(_Req("x", "6.6.6.6,203.0.113.7, 172.71.0.1, 10.28.0.9")) == "203.0.113.7"
