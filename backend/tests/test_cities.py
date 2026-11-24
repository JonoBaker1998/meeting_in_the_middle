from backend.app.data.cities import CITIES, PREFS, MODES
from backend.app.data.hotspots import HOT_NEIGHBOURHOODS
from backend.app.geo import LatLng, distance_m, offset


def test_four_cities_three_people_each():
    assert set(CITIES) == {"capetown", "munich", "sf", "london"}
    for c in CITIES.values():
        assert len(c.people) == 3


def test_people_match_spec():
    names = {cid: [(p.name, p.area) for p in c.people] for cid, c in CITIES.items()}
    assert names["capetown"] == [("Alex", "Sea Point"), ("Sam", "Observatory"), ("Jo", "Claremont")]
    assert names["munich"] == [("Alex", "Schwabing"), ("Sam", "Sendling"), ("Jo", "Haidhausen")]
    assert names["sf"] == [("Alex", "Mission"), ("Sam", "Inner Richmond"), ("Jo", "North Beach")]
    assert names["london"] == [("Alex", "Camden"), ("Sam", "Brixton"), ("Jo", "Hammersmith")]


def test_modes_and_defaults():
    assert CITIES["capetown"].modes == ("bike", "car") and CITIES["capetown"].default_mode == "car"
    for cid in ("munich", "sf", "london"):
        assert CITIES[cid].modes == MODES and CITIES[cid].default_mode == "transit"


def test_candidates_and_bounds():
    for c in CITIES.values():
        assert 8 <= len(c.candidates) <= 12
        assert len({a.name for a in c.candidates}) == len(c.candidates)
        assert all(c.contains(a.at) for a in c.candidates)
        assert all(c.contains(p.at) for p in c.people)
        assert len(c.heat_centres) >= 5


def test_mockup_areas_are_candidates():
    want = {"munich": {"Sendlinger Tor", "Gärtnerplatz", "Maxvorstadt (Uni)", "Glockenbachviertel"},
            "sf": {"Hayes Valley", "Lower Polk", "Mission / Valencia St", "SoMa / Yerba Buena"},
            "capetown": {"Gardens / Kloof Street", "Bree Street", "Woodstock / Albert Road", "De Waterkant"},
            "london": {"Soho", "Covent Garden", "Southbank / Waterloo", "Shoreditch"}}
    for cid, names in want.items():
        assert names <= {a.name for a in CITIES[cid].candidates}


def test_candidates_and_heat_come_from_researched_hotspots():
    for cid, c in CITIES.items():
        researched = {h["name"] for h in HOT_NEIGHBOURHOODS[cid]}
        assert {a.name for a in c.candidates} <= researched
        assert all(0 < w <= 1 for _, w in c.heat_centres)


def test_hotspot_entries_are_complete():
    for cid, spots in HOT_NEIGHBOURHOODS.items():
        for h in spots:
            assert set(h) >= {"name", "lat", "lng", "known_for", "weight", "candidate"}


def test_prefs():
    assert PREFS["food"] == ("Asian", "Sushi", "Burgers", "Italian", "Pizza", "Mexican", "Vegetarian", "Steak")
    assert PREFS["drinks"] == ("Cocktails", "Wine", "Craft beer", "Rooftop", "Pub")


def test_geo_roundtrip():
    a = LatLng(48.1340, 11.5670)
    b = offset(a, 300, 400)
    assert abs(distance_m(a, b) - 500) < 2
