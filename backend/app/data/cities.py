"""Demo cities: who is meeting, which areas are candidate spots, where the heat is."""

from dataclasses import dataclass

from backend.app.data.hotspots import HOT_NEIGHBOURHOODS
from backend.app.geo import LatLng

MODES = ("transit", "bike", "car")

PREFS: dict[str, tuple[str, ...]] = {
    "food": ("Asian", "Sushi", "Burgers", "Italian", "Pizza", "Mexican", "Vegetarian", "Steak"),
    "drinks": ("Cocktails", "Wine", "Craft beer", "Rooftop", "Pub"),
}

BOUNDS_MARGIN_DEG = 0.02  # roughly 2 km


@dataclass(frozen=True)
class Area:
    name: str
    at: LatLng


@dataclass(frozen=True)
class Person:
    name: str
    area: str
    at: LatLng


@dataclass(frozen=True)
class City:
    id: str
    name: str
    people: tuple[Person, ...]
    candidates: tuple[Area, ...]
    modes: tuple[str, ...]
    default_mode: str
    bounds: tuple[float, float, float, float]  # south, west, north, east
    heat_centres: tuple[tuple[LatLng, float], ...]  # (centre, weight)

    def contains(self, p: LatLng) -> bool:
        s, w, n, e = self.bounds
        return s <= p.lat <= n and w <= p.lng <= e


def _build(city_id: str, name: str, people: list[tuple[str, str, float, float]],
           modes: tuple[str, ...], default_mode: str) -> City:
    spots = HOT_NEIGHBOURHOODS[city_id]
    persons = tuple(Person(n, area, LatLng(lat, lng)) for n, area, lat, lng in people)
    candidates = tuple(Area(h["name"], LatLng(h["lat"], h["lng"])) for h in spots if h["candidate"])
    heat = tuple((LatLng(h["lat"], h["lng"]), h["weight"]) for h in spots)
    pts = [p.at for p in persons] + [c for c, _ in heat]
    bounds = (min(p.lat for p in pts) - BOUNDS_MARGIN_DEG, min(p.lng for p in pts) - BOUNDS_MARGIN_DEG,
              max(p.lat for p in pts) + BOUNDS_MARGIN_DEG, max(p.lng for p in pts) + BOUNDS_MARGIN_DEG)
    return City(city_id, name, persons, candidates, modes, default_mode, bounds, heat)


CITIES: dict[str, City] = {
    "capetown": _build("capetown", "Cape Town", [
        ("Alex", "Sea Point", -33.9150, 18.3900),
        ("Sam", "Observatory", -33.9380, 18.4720),
        ("Jo", "Claremont", -33.9820, 18.4650),
    ], modes=("bike", "car"), default_mode="car"),
    "munich": _build("munich", "Munich", [
        ("Alex", "Schwabing", 48.1622, 11.5860),
        ("Sam", "Sendling", 48.1180, 11.5480),
        ("Jo", "Haidhausen", 48.1300, 11.5990),
    ], modes=MODES, default_mode="transit"),
    "sf": _build("sf", "San Francisco", [
        ("Alex", "Mission", 37.7599, -122.4148),
        ("Sam", "Inner Richmond", 37.7800, -122.4630),
        ("Jo", "North Beach", 37.8003, -122.4100),
    ], modes=MODES, default_mode="transit"),
    "london": _build("london", "London", [
        ("Alex", "Camden", 51.5390, -0.1426),
        ("Sam", "Brixton", 51.4613, -0.1156),
        ("Jo", "Hammersmith", 51.4927, -0.2240),
    ], modes=MODES, default_mode="transit"),
}
