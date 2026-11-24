"""Fairness ranking: which spots are fairest for the group, and what's there.

Rules (from the design):
- Fairest = smallest longest trip; ties broken by spread (longest - shortest),
  then by name so results are stable.
- Fair zone = longest trip within FAIR_ZONE_MIN minutes of the best.
- Top list = up to MAX_SPOTS fair-zone spots that have at least one place
  matching the kind + preferences; fair-zone spots without a match are skipped.
- "Your spot" (dragged) is always evaluated, wherever it is.
"""

from dataclasses import dataclass

from backend.app.data.cities import City
from backend.app.geo import LatLng, distance_m
from backend.app.providers.base import Place, Provider

FAIR_ZONE_MIN = 5
MAX_SPOTS = 3
WALK_M_PER_MIN = 80


@dataclass
class SpotResult:
    id: str
    name: str
    at: LatLng
    times: list[int]
    longest: int
    spread: int
    in_fair_zone: bool
    matching: int


@dataclass
class PlaceResult:
    place: Place
    times: list[int]
    walk_min: int
    distance_m: int


@dataclass
class RankResult:
    spots: list[SpotResult]
    skipped: list[SpotResult]
    candidates: list[SpotResult]
    best_longest: int


def _matches(place: Place, kind: str, prefs: set[str]) -> bool:
    return place.kind == kind and (not prefs or place.type in prefs)


def _matching_places(provider: Provider, city: City, at: LatLng, kind: str,
                     prefs: set[str], radius_m: int) -> list[Place]:
    return [p for p in provider.places(city, at, radius_m, kind) if _matches(p, kind, prefs)]


def _origins(city: City, modes: list[str]):
    return list(zip(city.people, modes))


def _spot(id_: str, name: str, at: LatLng, times: list[int], best_longest: int, matching: int) -> SpotResult:
    longest = max(times)
    return SpotResult(id_, name, at, times, longest, longest - min(times),
                      longest <= best_longest + FAIR_ZONE_MIN, matching)


def rank(provider: Provider, city: City, modes: list[str], kind: str,
         prefs: set[str], radius_m: int) -> RankResult:
    areas = list(city.candidates)
    matrix = provider.travel_times(city, _origins(city, modes), [a.at for a in areas])
    columns = [[row[j] for row in matrix] for j in range(len(areas))]
    best = min(max(col) for col in columns)
    candidates = [
        _spot(a.name, a.name, a.at, col, best,
              len(_matching_places(provider, city, a.at, kind, prefs, radius_m)))
        for a, col in zip(areas, columns)
    ]
    spots, skipped = [], []
    for s in sorted(candidates, key=lambda s: (s.longest, s.spread, s.name)):
        if not s.in_fair_zone or len(spots) == MAX_SPOTS:
            break
        (spots if s.matching > 0 else skipped).append(s)
    return RankResult(spots, skipped, candidates, best)


def evaluate_spot(provider: Provider, city: City, modes: list[str], kind: str, prefs: set[str],
                  radius_m: int, at: LatLng, best_longest: int,
                  id: str = "custom", name: str = "Your spot") -> SpotResult:
    times = [row[0] for row in provider.travel_times(city, _origins(city, modes), [at])]
    return _spot(id, name, at, times, best_longest,
                 len(_matching_places(provider, city, at, kind, prefs, radius_m)))


def places_for(provider: Provider, city: City, modes: list[str], at: LatLng, kind: str,
               prefs: set[str], radius_m: int) -> list[PlaceResult]:
    places = _matching_places(provider, city, at, kind, prefs, radius_m)
    if not places:
        return []
    matrix = provider.travel_times(city, _origins(city, modes), [p.at for p in places])
    results = []
    for j, p in enumerate(places):
        d = round(distance_m(at, p.at))
        results.append(PlaceResult(p, [row[j] for row in matrix], max(1, round(d / WALK_M_PER_MIN)), d))
    return sorted(results, key=lambda r: (max(r.times), r.distance_m))
