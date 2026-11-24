"""Small geography helpers (metres, straight lines)."""

import math
from typing import NamedTuple

EARTH_RADIUS_M = 6_371_000


class LatLng(NamedTuple):
    lat: float
    lng: float


def distance_m(a: LatLng, b: LatLng) -> float:
    """Great-circle distance in metres (haversine)."""
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def offset(origin: LatLng, east_m: float, north_m: float) -> LatLng:
    """Point `east_m` east and `north_m` north of origin (good enough at city scale)."""
    dlat = north_m / EARTH_RADIUS_M
    dlng = east_m / (EARTH_RADIUS_M * math.cos(math.radians(origin.lat)))
    return LatLng(origin.lat + math.degrees(dlat), origin.lng + math.degrees(dlng))
