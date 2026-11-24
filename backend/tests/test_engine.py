from collections import Counter

from backend.app import engine
from backend.app.data.cities import CITIES
from backend.app.geo import LatLng, offset
from backend.app.providers.base import Place
from backend.app.providers.fake import FakeProvider


class StubProvider:
    """times[area_name] = [alex, sam, jo]; places[area_name] = [types...]"""

    def __init__(self, city, times, places):
        self.city, self.t, self.p, self.calls = city, times, places, Counter()
        self.by_pos = {(a.at.lat, a.at.lng): a.name for a in city.candidates}

    def travel_times(self, city, origins, dests):
        out = [[0] * len(dests) for _ in origins]
        for j, d in enumerate(dests):
            name = self.by_pos.get((d.lat, d.lng))
            for i in range(len(origins)):
                out[i][j] = self.t[name][i] if name else 99
        return out

    def places(self, city, centre, radius_m, kind):
        name = self.by_pos.get((centre.lat, centre.lng))
        return [Place(f"Sample {t}", t, kind, 4.5, "$$", offset(centre, 100, 0))
                for t in self.p.get(name, [])]


def make(times, places):
    city = CITIES["munich"]
    names = [a.name for a in city.candidates]
    full_t = {n: times.get(n, [60, 60, 60]) for n in names}
    return city, StubProvider(city, full_t, places)


M = ["transit"] * 3


def test_longest_trip_wins_then_spread():
    city, p = make({"Sendlinger Tor": [17, 14, 15], "Gärtnerplatz": [16, 17, 12], "Glockenbachviertel": [17, 16, 16]},
                   {"Sendlinger Tor": ["Sushi"], "Gärtnerplatz": ["Sushi"], "Glockenbachviertel": ["Sushi"]})
    r = engine.rank(p, city, M, "food", set(), 800)
    # all longest 17; spreads 1 (Glockenbach), 3 (Sendlinger), 5 (Gärtnerplatz)
    assert [s.name for s in r.spots] == ["Glockenbachviertel", "Sendlinger Tor", "Gärtnerplatz"]
    assert r.best_longest == 17


def test_fair_zone_boundary_is_inclusive_5():
    city, p = make({"Sendlinger Tor": [10, 10, 10], "Gärtnerplatz": [15, 9, 9], "Glockenbachviertel": [16, 9, 9]},
                   {"Sendlinger Tor": ["Pizza"], "Gärtnerplatz": ["Pizza"], "Glockenbachviertel": ["Pizza"]})
    r = engine.rank(p, city, M, "food", set(), 800)
    assert [s.name for s in r.spots] == ["Sendlinger Tor", "Gärtnerplatz"]
    assert all(s.in_fair_zone for s in r.spots)


def test_spot_without_match_is_skipped_and_replaced_within_zone():
    city, p = make({"Sendlinger Tor": [10, 10, 10], "Gärtnerplatz": [11, 10, 10],
                    "Glockenbachviertel": [12, 10, 10], "Maxvorstadt (Uni)": [13, 10, 10]},
                   {"Sendlinger Tor": ["Sushi"], "Gärtnerplatz": ["Pizza"],
                    "Glockenbachviertel": ["Sushi"], "Maxvorstadt (Uni)": ["Sushi"]})
    r = engine.rank(p, city, M, "food", {"Sushi"}, 800)
    assert [s.name for s in r.spots] == ["Sendlinger Tor", "Glockenbachviertel", "Maxvorstadt (Uni)"]
    assert [s.name for s in r.skipped] == ["Gärtnerplatz"]


def test_never_fills_from_outside_fair_zone():
    city, p = make({"Sendlinger Tor": [10, 10, 10], "Gärtnerplatz": [30, 10, 10]},
                   {"Sendlinger Tor": ["Sushi"], "Gärtnerplatz": ["Sushi"]})
    r = engine.rank(p, city, M, "food", set(), 800)
    assert [s.name for s in r.spots] == ["Sendlinger Tor"]


def test_rank_returns_empty_when_nothing_matches():
    city, p = make({"Sendlinger Tor": [10, 10, 10]}, {"Sendlinger Tor": ["Pizza"]})
    r = engine.rank(p, city, M, "food", {"Steak"}, 800)
    assert r.spots == []
    assert "Sendlinger Tor" in [s.name for s in r.skipped]


def test_no_prefs_means_any_place_counts():
    city, p = make({"Sendlinger Tor": [10, 10, 10]}, {"Sendlinger Tor": ["Bistro"]})
    assert engine.rank(p, city, M, "food", set(), 800).spots[0].matching == 1


def test_custom_spot_far_away_still_evaluated():
    city, p = make({"Sendlinger Tor": [10, 10, 10]}, {"Sendlinger Tor": ["Pizza"]})
    s = engine.evaluate_spot(p, city, M, "food", set(), 800, LatLng(48.20, 11.50), best_longest=10)
    assert s.id == "custom" and s.longest == 99 and not s.in_fair_zone and s.matching == 0


def test_candidates_cover_every_area():
    city, p = make({}, {})
    r = engine.rank(p, city, M, "food", set(), 800)
    assert len(r.candidates) == len(city.candidates)
    assert all(c.matching == 0 for c in r.candidates)


def test_places_for_real_provider():
    p, city = FakeProvider(), CITIES["munich"]
    at = city.candidates[0].at
    res = engine.places_for(p, city, M, at, "food", {"Sushi", "Pizza"}, 1500)
    assert res
    assert all(len(r.times) == 3 for r in res)
    assert all(r.place.type in {"Sushi", "Pizza"} for r in res)
    keys = [(max(r.times), r.distance_m) for r in res]
    assert keys == sorted(keys)
    assert all(r.walk_min == max(1, round(r.distance_m / 80)) for r in res)
    assert p.calls["travel_times"] == 3 * len(res)
