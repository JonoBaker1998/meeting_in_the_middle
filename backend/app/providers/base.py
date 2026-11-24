"""The provider seam: everything the engine needs from a maps/places service.

FakeProvider implements this for the PoC; a Google-backed provider can
implement it later without the engine or the website changing.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from backend.app.data.cities import City, Person
from backend.app.geo import LatLng


@dataclass(frozen=True)
class Place:
    name: str
    type: str  # one of PREFS[kind], or "Bistro" for food
    kind: str  # "food" or "drinks"
    rating: float
    price: str  # "$", "$$", "$$$"
    at: LatLng


@dataclass(frozen=True)
class RouteStep:
    icon: str  # walk, train, bus, tram, bike, car, info
    text: str


class Provider(Protocol):
    calls: Counter

    def travel_times(self, city: City, origins: list[tuple[Person, str]],
                     dests: list[LatLng]) -> list[list[int]]:
        """Whole minutes, indexed [person][dest]; each person uses their own mode."""

    def route(self, city: City, person: Person, mode: str, dest: LatLng) -> list[RouteStep]:
        """Step-by-step directions for one person to one spot."""

    def places(self, city: City, centre: LatLng, radius_m: int, kind: str) -> list[Place]:
        """Places of `kind` within `radius_m` of centre, nearest first."""

    def heat(self, city: City) -> list[tuple[float, float, float]]:
        """(lat, lng, weight 0-1) points showing where top-rated places cluster."""
