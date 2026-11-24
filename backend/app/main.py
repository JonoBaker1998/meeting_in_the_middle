"""FastAPI application: JSON API for Meet in the Middle, plus the static website."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.app import engine
from backend.app.data.cities import CITIES, PREFS, City
from backend.app.geo import LatLng
from backend.app.providers.base import Provider
from backend.app.providers.fake import FakeProvider
from backend.app.schemas import (RADIUS_DEFAULT, RADIUS_MAX, RADIUS_MIN, RADIUS_STEP, Mode,
                                 SearchRequest)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def _at(p: LatLng) -> dict:
    return {"lat": p.lat, "lng": p.lng}


def _spot_out(s: engine.SpotResult) -> dict:
    return {"id": s.id, "name": s.name, "at": _at(s.at), "times": s.times, "longest": s.longest,
            "spread": s.spread, "in_fair_zone": s.in_fair_zone, "matching": s.matching}


def _place_out(r: engine.PlaceResult) -> dict:
    p = r.place
    return {"name": p.name, "type": p.type, "rating": p.rating, "price": p.price,
            "at": _at(p.at), "times": r.times, "walk_min": r.walk_min}


def _city_or_404(city_id: str) -> City:
    city = CITIES.get(city_id)
    if city is None:
        raise HTTPException(404, detail=f"Unknown city {city_id!r}")
    return city


def _check_inside(city: City, at: LatLng) -> None:
    if not city.contains(at):
        raise HTTPException(422, detail=f"That point is outside {city.name}")


def create_app(provider: Provider | None = None) -> FastAPI:
    provider = provider or FakeProvider()
    app = FastAPI(title="Meet in the Middle")

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/cities")
    def cities() -> dict:
        return {
            "cities": [{
                "id": c.id, "name": c.name, "modes": list(c.modes), "default_mode": c.default_mode,
                "bounds": list(c.bounds),
                "people": [{"name": p.name, "area": p.area, "at": _at(p.at)} for p in c.people],
            } for c in CITIES.values()],
            "prefs": {k: list(v) for k, v in PREFS.items()},
            "radius": {"min": RADIUS_MIN, "max": RADIUS_MAX, "step": RADIUS_STEP, "default": RADIUS_DEFAULT},
        }

    @app.post("/api/search")
    def search(req: SearchRequest) -> dict:
        city = _city_or_404(req.city)
        if len(req.modes) != len(city.people):
            raise HTTPException(422, detail=f"{city.name} has {len(city.people)} people; got {len(req.modes)} modes")
        bad = sorted(set(req.modes) - set(city.modes))
        if bad:
            raise HTTPException(422, detail=f"{', '.join(bad)} not available in {city.name}")
        custom_at = LatLng(req.custom.lat, req.custom.lng) if req.custom else None
        if custom_at:
            _check_inside(city, custom_at)

        modes, prefs = list(req.modes), set(req.prefs)
        r = engine.rank(provider, city, modes, req.kind, prefs, req.radius_m)
        custom = (engine.evaluate_spot(provider, city, modes, req.kind, prefs, req.radius_m,
                                       custom_at, r.best_longest) if custom_at else None)

        if req.selected == "custom" and custom:
            selected = custom
        else:
            selected = next((s for s in r.spots if s.id == req.selected), r.spots[0] if r.spots else None)
        places = (engine.places_for(provider, city, modes, selected.at, req.kind, prefs, req.radius_m)
                  if selected else [])

        return {
            "spots": [_spot_out(s) for s in r.spots],
            "skipped": [{"id": s.id, "name": s.name} for s in r.skipped],
            "custom": _spot_out(custom) if custom else None,
            "selected": selected.id if selected else None,
            "places": [_place_out(p) for p in places],
            "candidates": [{"name": c.name, "at": _at(c.at), "over_best": c.longest - r.best_longest,
                            "matching": c.matching} for c in r.candidates],
        }

    @app.get("/api/route")
    def route(city: str = Query(max_length=32), person: int = Query(ge=0),
              mode: Mode = Query(), lat: float = Query(ge=-90, le=90),
              lng: float = Query(ge=-180, le=180)) -> dict:
        c = _city_or_404(city)
        if person >= len(c.people):
            raise HTTPException(422, detail="Unknown person")
        if mode not in c.modes:
            raise HTTPException(422, detail=f"{mode} not available in {c.name}")
        dest = LatLng(lat, lng)
        _check_inside(c, dest)
        steps = provider.route(c, c.people[person], mode, dest)
        return {"steps": [{"icon": s.icon, "text": s.text} for s in steps]}

    @app.get("/api/heat")
    def heat(city: str = Query(max_length=32)) -> dict:
        return {"points": [list(p) for p in provider.heat(_city_or_404(city))]}

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
