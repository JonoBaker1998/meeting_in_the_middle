import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.providers.fake import FakeProvider


@pytest.fixture
def client():
    return TestClient(create_app())


def body(**kw):
    b = {"city": "munich", "modes": ["transit"] * 3, "kind": "food", "prefs": [], "radius_m": 800}
    b.update(kw)
    return b


def test_cities(client):
    j = client.get("/api/cities").json()
    assert [c["id"] for c in j["cities"]] == ["capetown", "munich", "sf", "london"]
    assert j["radius"] == {"min": 300, "max": 1500, "step": 100, "default": 800}
    assert j["prefs"]["drinks"] == ["Cocktails", "Wine", "Craft beer", "Rooftop", "Pub"]
    ct = j["cities"][0]
    assert ct["modes"] == ["bike", "car"] and ct["default_mode"] == "car"
    assert ct["people"][0] == {"name": "Alex", "area": "Sea Point", "at": {"lat": -33.915, "lng": 18.39}}


def test_search_returns_up_to_three_fair_spots_with_places(client):
    j = client.post("/api/search", json=body()).json()
    assert 1 <= len(j["spots"]) <= 3
    assert all(s["in_fair_zone"] and s["matching"] >= 1 for s in j["spots"])
    assert j["selected"] == j["spots"][0]["id"]
    assert j["places"] and all(len(p["times"]) == 3 for p in j["places"])
    assert set(j["places"][0]) == {"name", "type", "rating", "price", "at", "times", "walk_min"}
    assert len(j["candidates"]) >= 8
    assert set(j["candidates"][0]) == {"name", "at", "over_best", "matching"}


def test_search_selects_requested_spot(client):
    first = client.post("/api/search", json=body()).json()
    assert len(first["spots"]) > 1
    second = first["spots"][1]["id"]
    j = client.post("/api/search", json=body(selected=second)).json()
    assert j["selected"] == second
    assert j["places"] and j["places"] != first["places"]


def test_search_selected_and_custom(client):
    j = client.post("/api/search", json=body(selected="custom", custom={"lat": 48.14, "lng": 11.57})).json()
    assert j["custom"]["id"] == "custom" and j["selected"] == "custom"


class NoPlaces(FakeProvider):
    def places(self, city, centre, radius_m, kind):
        return []


def test_search_empty_state():
    j = TestClient(create_app(NoPlaces())).post("/api/search", json=body(prefs=["Steak"])).json()
    assert j["spots"] == [] and j["selected"] is None and j["places"] == []
    assert len(j["skipped"]) >= 1


def test_search_rejects_transit_in_cape_town(client):
    assert client.post("/api/search", json=body(city="capetown")).status_code == 422


def test_custom_spot_outside_bounds_rejected(client):
    assert client.post("/api/search", json=body(custom={"lat": 0.0, "lng": 0.0})).status_code == 422


@pytest.mark.parametrize("bad", [
    {"radius_m": 250}, {"radius_m": 1600}, {"radius_m": 850},
    {"prefs": ["Sushi"], "kind": "drinks"}, {"prefs": ["Nonsense"]},
    {"modes": ["transit"] * 2}, {"modes": ["transit"] * 9}, {"modes": ["plane"] * 3},
])
def test_search_validation(client, bad):
    assert client.post("/api/search", json=body(**bad)).status_code == 422


def test_unknown_city_404(client):
    assert client.post("/api/search", json=body(city="paris")).status_code == 404


def test_route_and_heat(client):
    ok = {"city": "london", "person": 0, "mode": "transit", "lat": 51.513, "lng": -0.135}
    r = client.get("/api/route", params=ok)
    assert r.status_code == 200 and r.json()["steps"][0] == {"icon": "walk", "text": r.json()["steps"][0]["text"]}
    assert client.get("/api/route", params=dict(ok, person=5)).status_code == 422
    assert client.get("/api/route", params=dict(ok, city="capetown", lat=-33.92, lng=18.42)).status_code == 422
    assert client.get("/api/route", params=dict(ok, lat=0, lng=0)).status_code == 422
    assert len(client.get("/api/heat", params={"city": "sf"}).json()["points"]) >= 50
    assert client.get("/api/heat", params={"city": "paris"}).status_code == 404
