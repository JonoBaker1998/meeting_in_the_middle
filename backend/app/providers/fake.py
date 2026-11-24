"""Deterministic fake data that looks plausible: travel times, routes, places, heat.

Everything is seeded with hashlib (never Python's hash(), which changes per
process), so the same question always gets the same answer.
"""

import hashlib
import math
import random
from collections import Counter
from functools import lru_cache

from backend.app.data.cities import City, Person
from backend.app.geo import LatLng, distance_m, offset
from backend.app.providers.base import Place, RouteStep

# minutes = fixed overhead + km * detour / speed_kmh * 60
TIME_MODEL = {
    "transit": {"overhead": 8, "detour": 1.3, "speed_kmh": 22},
    "bike": {"overhead": 2, "detour": 1.25, "speed_kmh": 15},
    "car": {"overhead": 6, "detour": 1.4, "speed_kmh": 35},
}
MIN_MINUTES = 3

TRANSIT_LINES = {  # (icon, label) per city
    "munich": [("train", "U-Bahn"), ("train", "S-Bahn"), ("tram", "Tram")],
    "london": [("train", "Tube"), ("bus", "Bus"), ("train", "Overground")],
    "sf": [("train", "BART"), ("bus", "Muni bus"), ("train", "Muni Metro")],
}

# (name, type, base rating, price) — from the approved mockup
FOOD = [
    ("Sample Sushi Bar", "Sushi", 4.6, "$$"), ("Sample Omakase", "Sushi", 4.8, "$$$"),
    ("Sample Ramen House", "Asian", 4.5, "$"), ("Sample Thai Kitchen", "Asian", 4.3, "$"),
    ("Sample Dumpling Bar", "Asian", 4.4, "$"),
    ("Sample Burger Joint", "Burgers", 4.4, "$"), ("Sample Smash Burgers", "Burgers", 4.2, "$"),
    ("Sample Trattoria", "Italian", 4.3, "$$"), ("Sample Pizzeria", "Pizza", 4.6, "$"),
    ("Sample Taqueria", "Mexican", 4.4, "$"), ("Sample Veggie Kitchen", "Vegetarian", 4.7, "$$"),
    ("Sample Grill House", "Steak", 4.2, "$$$"), ("Sample Bistro", "Bistro", 4.5, "$$"),
]
DRINKS = [
    ("Sample Cocktail Lounge", "Cocktails", 4.5, "$$$"), ("Sample Speakeasy", "Cocktails", 4.8, "$$"),
    ("Sample Wine Bar", "Wine", 4.6, "$$"), ("Sample Natural Wine Shop", "Wine", 4.4, "$$"),
    ("Sample Taproom", "Craft beer", 4.4, "$"), ("Sample Brewery", "Craft beer", 4.3, "$"),
    ("Sample Rooftop", "Rooftop", 4.1, "$$$"), ("Sample Corner Pub", "Pub", 4.3, "$"),
    ("Sample Sports Bar", "Pub", 3.9, "$"),
]
TEMPLATES = {"food": FOOD, "drinks": DRINKS}
# Busier hotspots (higher weight) offer more variety: share of types kept = 0.4 + 0.5 * weight.
TYPE_SHARE_BASE, TYPE_SHARE_PER_WEIGHT = 0.4, 0.5
PLACES_PER_AREA = (6, 10)  # plus up to 4 more for the strongest hotspots
SCATTER_M = (50, 1200)
HEAT_POINTS_PER_WEIGHT = 12
HEAT_SPREAD_M = 650


def _seed(*parts) -> int:
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16], 16)


def _short(area_name: str) -> str:
    return area_name.split(" (")[0].split(" /")[0]


def _check_mode(city: City, mode: str) -> None:
    if mode not in city.modes:
        raise ValueError(f"{mode!r} is not available in {city.name}")


class FakeProvider:
    def __init__(self) -> None:
        self.calls: Counter = Counter()

    # --- travel times -----------------------------------------------------
    def _minutes(self, city: City, person: Person, mode: str, dest: LatLng) -> int:
        m = TIME_MODEL[mode]
        km = distance_m(person.at, dest) / 1000
        base = m["overhead"] + km * m["detour"] / m["speed_kmh"] * 60
        jitter = _seed(city.id, person.name, mode, f"{dest.lat:.4f}", f"{dest.lng:.4f}") % 5 - 2
        return max(MIN_MINUTES, round(base + jitter))

    def travel_times(self, city, origins, dests):
        for _, mode in origins:
            _check_mode(city, mode)
        self.calls["travel_times"] += len(origins) * len(dests)
        return [[self._minutes(city, person, mode, d) for d in dests] for person, mode in origins]

    # --- routes -----------------------------------------------------------
    def route(self, city, person, mode, dest):
        _check_mode(city, mode)
        self.calls["route"] += 1
        total = self._minutes(city, person, mode, dest)
        km = distance_m(person.at, dest) / 1000
        if mode == "bike":
            return [RouteStep("bike", f"Cycle {km * 1.25:.1f} km ({total} min)"),
                    RouteStep("info", "Mostly quiet streets and bike lanes")]
        if mode == "car":
            return [RouteStep("car", f"Drive {km * 1.4:.1f} km ({total} min)"),
                    RouteStep("info", "Includes a few minutes to park")]
        rng = random.Random(_seed(city.id, person.name, "route", f"{dest.lat:.4f}", f"{dest.lng:.4f}"))
        lines = TRANSIT_LINES[city.id]
        walk_start, walk_end = rng.randint(2, 6), rng.randint(2, 6)
        ride = max(2, total - walk_start - walk_end)
        steps = [RouteStep("walk", f"Walk {walk_start} min to the nearest stop")]
        if ride > 15:
            first = ride // 2 + rng.randint(-2, 2)
            legs = [(rng.choice(lines), first), (rng.choice(lines), ride - first)]
        else:
            legs = [(rng.choice(lines), ride)]
        for i, ((icon, label), mins) in enumerate(legs):
            prefix = "Change, then " if i else ""
            steps.append(RouteStep(icon, f"{prefix}{label} · {max(1, mins // 2)} stops ({mins} min)"))
        steps.append(RouteStep("walk", f"Walk {walk_end} min to the meeting spot"))
        return steps

    # --- places -----------------------------------------------------------
    def places(self, city, centre, radius_m, kind):
        self.calls["places"] += 1
        found = [(distance_m(centre, p.at), p) for p in _place_pool(city.id, kind)]
        return [p for d, p in sorted(found, key=lambda x: x[0]) if d <= radius_m]

    # --- heat -------------------------------------------------------------
    def heat(self, city):
        self.calls["heat"] += 1
        pts = []
        for k, (c, weight) in enumerate(city.heat_centres):
            rng = random.Random(_seed(city.id, "heat", k))
            for _ in range(max(4, round(HEAT_POINTS_PER_WEIGHT * weight))):
                ang, dist = rng.uniform(0, 2 * math.pi), rng.random() ** 1.6 * HEAT_SPREAD_M
                p = offset(c, math.cos(ang) * dist, math.sin(ang) * dist)
                pts.append((p.lat, p.lng, round(weight * rng.uniform(0.6, 1.0), 3)))
        return pts


@lru_cache(maxsize=None)
def _place_pool(city_id: str, kind: str) -> tuple[Place, ...]:
    """City-wide pool, so any point in the city (incl. a dragged spot) has places."""
    from backend.app.data.hotspots import HOT_NEIGHBOURHOODS

    templates = TEMPLATES[kind]
    all_types = sorted({t[1] for t in templates})
    pool = []
    for h in HOT_NEIGHBOURHOODS[city_id]:
        rng = random.Random(_seed(city_id, h["name"], kind))
        share = TYPE_SHARE_BASE + TYPE_SHARE_PER_WEIGHT * h["weight"]
        kept = set(rng.sample(all_types, min(len(all_types), math.ceil(len(all_types) * share))))
        options = [t for t in templates if t[1] in kept]
        centre = LatLng(h["lat"], h["lng"])
        for i in range(rng.randint(*PLACES_PER_AREA) + round(4 * h["weight"])):
            name, ptype, rating, price = options[i % len(options)] if i < len(options) else rng.choice(options)
            ang, dist = rng.uniform(0, 2 * math.pi), rng.uniform(*SCATTER_M)
            pool.append(Place(
                name=f"{name} — {_short(h['name'])}" + (f" {i + 1}" if i >= len(options) else ""),
                type=ptype, kind=kind,
                rating=round(min(5.0, rating + rng.uniform(-0.3, 0.2)), 1),
                price=price, at=offset(centre, math.cos(ang) * dist, math.sin(ang) * dist)))
    return tuple(pool)
