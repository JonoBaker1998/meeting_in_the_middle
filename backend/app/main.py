"""FastAPI application: JSON API for Meet in the Middle, plus the static website."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from backend.app import engine
from backend.app.data.cities import CITIES, PREFS, City
from backend.app.geo import LatLng
from backend.app.providers.base import Provider
from backend.app.providers.fake import FakeProvider
from backend.app.schemas import (RADIUS_DEFAULT, RADIUS_MAX, RADIUS_MIN, RADIUS_STEP, Mode,
                                 SearchRequest)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

DEFAULTS = {
    "RATE_LIMIT_SEARCH": "30/minute",
    "RATE_LIMIT_DEFAULT": "60/minute",
    "ALLOWED_ORIGINS": "http://localhost:8000,http://127.0.0.1:8000,https://jonobaker1998.github.io",
    "MAX_BODY_BYTES": "10240",
}
TOO_MANY = "Too many requests — please slow down."
TOO_LARGE = "Request too large."


def _setting(name: str) -> str:
    return os.environ.get(name, DEFAULTS[name])


def client_key(request) -> str:
    """Rate-limit key: the visitor's IP.

    Locally (TRUSTED_PROXY_HOPS=0, the default) this is the connection's IP and
    X-Forwarded-For is ignored. Behind Render's proxy (TRUSTED_PROXY_HOPS=1) the
    real IP is the entry the proxy appended: the Nth from the RIGHT. Entries to
    the left came from the visitor and can be faked, so they are never used.
    """
    hops = int(os.environ.get("TRUSTED_PROXY_HOPS", "0"))
    forwarded = request.headers.get("x-forwarded-for") if hops > 0 else None
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "unknown"


class _TooLarge(Exception):
    pass


class BodySizeLimit:
    """Reject request bodies over max_bytes with 413, whether or not Content-Length is sent."""

    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.max_bytes):
            return await JSONResponse({"detail": TOO_LARGE}, 413)(scope, receive, send)
        seen = 0

        async def limited_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    raise _TooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _TooLarge:
            await JSONResponse({"detail": TOO_LARGE}, 413)(scope, receive, send)


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

    limiter = Limiter(key_func=client_key)  # fresh in-memory counters per app
    app.state.limiter = limiter
    search_limit, default_limit = _setting("RATE_LIMIT_SEARCH"), _setting("RATE_LIMIT_DEFAULT")

    @app.exception_handler(RateLimitExceeded)
    async def _too_many(request: Request, exc: RateLimitExceeded):
        return JSONResponse({"detail": TOO_MANY}, status_code=429)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/cities")
    @limiter.limit(default_limit)
    def cities(request: Request) -> dict:
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
    @limiter.limit(search_limit)
    def search(request: Request, req: SearchRequest) -> dict:
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
    @limiter.limit(default_limit)
    def route(request: Request, city: str = Query(max_length=32), person: int = Query(ge=0),
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
    @limiter.limit(default_limit)
    def heat(request: Request, city: str = Query(max_length=32)) -> dict:
        return {"points": [list(p) for p in provider.heat(_city_or_404(city))]}

    # Added last = outermost, so 413 and 429 responses still carry CORS headers.
    app.add_middleware(BodySizeLimit, max_bytes=int(_setting("MAX_BODY_BYTES")))
    app.add_middleware(CORSMiddleware,
                       allow_origins=[o.strip() for o in _setting("ALLOWED_ORIGINS").split(",") if o.strip()],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    if FRONTEND_DIR.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
