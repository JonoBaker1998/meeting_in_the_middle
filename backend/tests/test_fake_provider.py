import pytest

from backend.app.data.cities import CITIES, PREFS
from backend.app.geo import LatLng, distance_m
from backend.app.providers.fake import FakeProvider


def test_times_deterministic_and_plausible():
    p, c = FakeProvider(), CITIES["munich"]
    origins = [(person, "transit") for person in c.people]
    dests = [a.at for a in c.candidates]
    t1 = p.travel_times(c, origins, dests)
    t2 = FakeProvider().travel_times(c, origins, dests)
    assert t1 == t2
    assert len(t1) == 3 and all(len(row) == len(dests) for row in t1)
    assert all(3 <= m <= 90 for row in t1 for m in row)


def test_closer_is_faster_same_mode():
    p, c = FakeProvider(), CITIES["london"]
    alex = c.people[0]
    near = min(c.candidates, key=lambda a: distance_m(alex.at, a.at))
    far = max(c.candidates, key=lambda a: distance_m(alex.at, a.at))
    [[t_near, t_far]] = p.travel_times(c, [(alex, "bike")], [near.at, far.at])
    assert t_near < t_far


def test_calls_counted_per_element():
    p, c = FakeProvider(), CITIES["sf"]
    p.travel_times(c, [(x, "car") for x in c.people], [a.at for a in c.candidates[:4]])
    assert p.calls["travel_times"] == 12


def test_transit_rejected_in_cape_town():
    c = CITIES["capetown"]
    with pytest.raises(ValueError):
        FakeProvider().travel_times(c, [(c.people[0], "transit")], [c.candidates[0].at])


def test_route_steps():
    c = CITIES["munich"]
    steps = FakeProvider().route(c, c.people[0], "transit", c.candidates[0].at)
    assert steps and steps[0].icon == "walk"
    assert all(s.text for s in steps)


def test_route_rejects_forbidden_mode():
    c = CITIES["capetown"]
    with pytest.raises(ValueError):
        FakeProvider().route(c, c.people[0], "transit", c.candidates[0].at)


def test_places_within_radius_sorted_and_typed():
    p, c = FakeProvider(), CITIES["munich"]
    centre = c.candidates[0].at
    places = p.places(c, centre, 800, "food")
    assert places
    d = [distance_m(centre, x.at) for x in places]
    assert all(v <= 800 for v in d) and d == sorted(d)
    assert all(x.name.startswith("Sample ") and x.kind == "food" for x in places)
    assert {x.type for x in places} <= set(PREFS["food"]) | {"Bistro"}


def test_places_vary_by_area_so_skipping_is_observable():
    p, c = FakeProvider(), CITIES["munich"]
    type_sets = [frozenset(x.type for x in p.places(c, a.at, 800, "food")) for a in c.candidates]
    assert any("Sushi" not in s for s in type_sets)
    assert any("Sushi" in s for s in type_sets)


def test_places_work_anywhere_in_city():
    p, c = FakeProvider(), CITIES["sf"]
    s, w, n, e = c.bounds
    mid = LatLng((s + n) / 2, (w + e) / 2)
    assert isinstance(p.places(c, mid, 1500, "drinks"), list)


def test_heat_points():
    pts = FakeProvider().heat(CITIES["london"])
    assert len(pts) >= 50
    assert all(0 < w <= 1 for _, _, w in pts)
