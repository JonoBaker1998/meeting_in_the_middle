# Meet in the Middle PoC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public website + Python API that finds the fairest meeting spots for a group (fake data, four cities) and shows restaurants/bars around them, matching the approved v4 mockup.

**Architecture:** FastAPI app with a provider seam (`FakeProvider` now, Google later) feeding a pure-Python ranking engine. A static plain-JS + Leaflet website calls the API; locally FastAPI serves both, online the site is on GitHub Pages and the API on Render's free plan, protected by rate limits, input limits and CORS.

**Tech Stack:** Python 3.12 (via uv), FastAPI 0.115.6, uvicorn 0.34.0, slowapi 0.1.9, pytest 8.3.4, httpx 0.28.1; HTML/CSS/ES-module JavaScript, Leaflet 1.9.4 (unpkg CDN), OpenStreetMap tiles.

**Spec:** `docs/superpowers/specs/2026-11-24-meet-in-the-middle-design.md`
**Mockup to reproduce (layout & behaviour, not numbers):** `.superpowers/brainstorm/mockups/layout-v4.html` (git-ignored; exists on the owner's machine)

## Global Constraints

- Python **3.12**, installed with **uv** into a project `.venv` (Homebrew is not installed; Anaconda's 3.7 stays untouched). No Node.js anywhere.
- Modes: `transit`, `bike`, `car`. **Cape Town allows only `bike` and `car`**, default `car`. Munich, San Francisco, London default `transit`.
- Fairness: rank by **longest trip** (min), tie-break **spread** (longest − shortest), then area name. **Fair zone = longest ≤ best longest + 5 min.**
- Top list: **at most 3** spots, **only from the fair zone**, each needing **≥ 1 matching place** within the radius; fewer → show fewer; none → empty state. Skipped spots are reported.
- "Your spot" (dragged) is always evaluated and shown with real stats, even outside the fair zone or with no matches.
- Radius: **300–1500 m, step 100, default 800**.
- Preferences — food: `Asian, Sushi, Burgers, Italian, Pizza, Mexican, Vegetarian, Steak`; drinks: `Cocktails, Wine, Craft beer, Rooftop, Pub`. Empty selection = everything.
- Places are named "Sample …"; UI shows a visible "Demo data" label.
- Abuse limits: search **30/minute per IP**; other endpoints 60/minute; **max 8 people**; request body ≤ **10 KB**; coordinates must be inside the city's bounds; CORS only for the Pages origin and localhost.
- No secrets in the repo or browser. Free plans only.
- Fake data must be deterministic across processes — **never use Python's built-in `hash()`** (it is randomised per process); use `hashlib`.

## Review Focus

1. **Real client IP behind Render's proxy** — rate limiting must key on the visitor, not Render's proxy; otherwise one visitor locks everyone out. Pinned by `test_rate_limit_uses_forwarded_for` (Task 6) and `--proxy-headers` in the start command (Task 8).
2. **Mode switch to a mode the city forbids** (e.g. a stale "transit" sent for Cape Town after switching city) → clear 422, not a crash. Pinned by `test_search_rejects_transit_in_cape_town` (Task 5).
3. **Preferences that match nothing anywhere** (e.g. Steak + Rooftop impossible combos, or Sushi only) → empty top list + skipped list + empty-state copy, never a 500 or an out-of-zone spot. Pinned by `test_rank_returns_empty_when_nothing_matches` (Task 4) and the UI check in Task 7.
4. **Dragged spot far outside the group / outside the city** → inside bounds: evaluated normally (big times, no places is fine); outside bounds: 422. Pinned by `test_custom_spot_outside_bounds_rejected` (Task 5) and `test_custom_spot_far_away_still_evaluated` (Task 4).
5. **Cold start / slow API** — first request can take 30–60 s on Render; the UI must show "Waking up the server…" and not spam requests while dragging the slider. Pinned by the debounce + wake-up checks in Task 7.

---

## File Structure

```
requirements.txt                 # runtime deps (Render installs this)
requirements-dev.txt             # -r requirements.txt + pytest, httpx
render.yaml                      # Render blueprint (Task 8)
.github/workflows/pages.yml      # publish frontend/ to GitHub Pages (Task 8)
backend/
  __init__.py
  app/
    __init__.py
    main.py                      # FastAPI app factory, routes, static mount, CORS, limiter
    schemas.py                   # pydantic request/response models + validation
    geo.py                       # distance + offset helpers
    data/
      __init__.py
      cities.py                  # City/Person/Area dataclasses, CITIES, PREFS
    providers/
      __init__.py
      base.py                    # Provider protocol, Place, RouteStep
      fake.py                    # FakeProvider (times, routes, places, heat)
    engine.py                    # fairness ranking, fair zone, prefs skipping, places_for
  tests/
    __init__.py
    test_health.py
    test_cities.py
    test_fake_provider.py
    test_engine.py
    test_api.py
    test_protection.py
frontend/
  index.html
  styles.css
  js/
    config.js                    # API base URL (same origin locally, Render URL on github.io)
    api.js                       # fetch wrappers, wake-up state, 429 handling
    state.js                     # app state + debounce
    map.js                       # Leaflet drawing
    panel.js                     # left panel rendering
    app.js                       # wiring
README.md                        # run locally, deploy, owner steps
```

---

### Task 1: Python environment and app skeleton

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `backend/__init__.py`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/tests/__init__.py`, `backend/tests/test_health.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `backend.app.main.create_app() -> FastAPI` and module-level `app = create_app()`; `GET /api/health` → `{"status": "ok"}`.

- [ ] **Step 1: Install uv and Python 3.12, create the venv** (no admin rights needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv python install 3.12
uv venv --python 3.12 .venv
```
Expected: `.venv/bin/python --version` prints `Python 3.12.x`.

- [ ] **Step 2: Write dependency files and install**

`requirements.txt`:
```
fastapi==0.115.6
uvicorn[standard]==0.34.0
slowapi==0.1.9
```
`requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.4
httpx==0.28.1
```
Run: `uv pip install --python .venv -r requirements-dev.txt` — Expected: installs without errors.

- [ ] **Step 3: Write the failing test** — `backend/tests/test_health.py`

```python
from fastapi.testclient import TestClient
from backend.app.main import create_app

def test_health():
    client = TestClient(create_app())
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 4: Run it** — `.venv/bin/pytest backend/tests/test_health.py -v` — Expected: FAIL (module not found).

- [ ] **Step 5: Implement `create_app()` in `backend/app/main.py`** with the health route; `app = create_app()` at module level.

- [ ] **Step 6: Run it** — Expected: PASS.

- [ ] **Step 7: Add a "Run locally" section to `README.md`** (the uv steps above, then `.venv/bin/uvicorn backend.app.main:app --reload`, then open http://localhost:8000).

- [ ] **Step 8: Commit**

```bash
git add requirements*.txt backend README.md
git commit -m "chore: python 3.12 env and FastAPI skeleton"
```

---

### Task 2: Demo cities and geo helpers

**Files:**
- Create: `backend/app/geo.py`, `backend/app/data/__init__.py`, `backend/app/data/cities.py`, `backend/tests/test_cities.py`

**Interfaces:**
- Produces (`geo.py`):
  - `class LatLng(NamedTuple): lat: float; lng: float`
  - `distance_m(a: LatLng, b: LatLng) -> float` (haversine)
  - `offset(origin: LatLng, east_m: float, north_m: float) -> LatLng`
- Produces (`cities.py`), all `@dataclass(frozen=True)`:
  - `Area(name: str, at: LatLng)`
  - `Person(name: str, area: str, at: LatLng)`
  - `City(id: str, name: str, people: tuple[Person, ...], candidates: tuple[Area, ...], modes: tuple[str, ...], default_mode: str, bounds: tuple[float, float, float, float]  # south, west, north, east, heat_centres: tuple[tuple[LatLng, float], ...]  # (centre, weight))`
  - `City.contains(p: LatLng) -> bool`
  - `CITIES: dict[str, City]` with ids `"capetown"`, `"munich"`, `"sf"`, `"london"`
  - `PREFS: dict[str, tuple[str, ...]]` with keys `"food"`, `"drinks"` (values from Global Constraints)
  - `MODES = ("transit", "bike", "car")`

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_cities.py`

```python
from backend.app.data.cities import CITIES, PREFS, MODES
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

def test_prefs():
    assert PREFS["food"] == ("Asian", "Sushi", "Burgers", "Italian", "Pizza", "Mexican", "Vegetarian", "Steak")
    assert PREFS["drinks"] == ("Cocktails", "Wine", "Craft beer", "Rooftop", "Pub")

def test_geo_roundtrip():
    a = LatLng(48.1340, 11.5670)
    b = offset(a, 300, 400)
    assert abs(distance_m(a, b) - 500) < 2
```

- [ ] **Step 2: Run** — `.venv/bin/pytest backend/tests/test_cities.py -v` — Expected: FAIL (imports).

- [ ] **Step 3: Implement `geo.py`.**

- [ ] **Step 4: Implement `cities.py`.** People and the four mockup areas per city use the coordinates in the mockup file (`CITIES` object, `hotspots` arrays). London people: Camden (51.5390, -0.1426), Brixton (51.4613, -0.1156), Hammersmith (51.4927, -0.2240). Add 4–8 more real neighbourhood candidates per city (London: also Victoria, Clapham, Islington, Kensington), heat centres = the busiest candidate areas plus at least one popular-but-unfair area per city (e.g. Munich Schwabing, SF Marina, Cape Town V&A Waterfront, London Notting Hill). Bounds: a box that comfortably contains people and candidates (~2 km margin).

- [ ] **Step 5: Run** — Expected: PASS.

- [ ] **Step 6: Commit** — `git add backend && git commit -m "feat: demo cities and geo helpers"`

---

### Task 3: Provider interface and FakeProvider

**Files:**
- Create: `backend/app/providers/__init__.py`, `backend/app/providers/base.py`, `backend/app/providers/fake.py`, `backend/tests/test_fake_provider.py`

**Interfaces:**
- Consumes: `City`, `Person`, `LatLng`, `distance_m`, `offset`, `PREFS` (Task 2).
- Produces (`base.py`):
  - `@dataclass(frozen=True) Place(name: str, type: str, kind: str, rating: float, price: str, at: LatLng)` — `kind` is `"food"`/`"drinks"`, `type` is one of `PREFS[kind]` or `"Bistro"` (food) — non-preference types are allowed but never match a selected preference.
  - `@dataclass(frozen=True) RouteStep(icon: str, text: str)` — icon in `walk, train, bus, tram, bike, car, info`.
  - `class Provider(Protocol)` with:
    - `travel_times(city: City, origins: list[tuple[Person, str]], dests: list[LatLng]) -> list[list[int]]` — `[person][dest]` whole minutes, each person uses their own mode.
    - `route(city: City, person: Person, mode: str, dest: LatLng) -> list[RouteStep]`
    - `places(city: City, centre: LatLng, radius_m: int, kind: str) -> list[Place]` — sorted by distance.
    - `heat(city: City) -> list[tuple[float, float, float]]` — `(lat, lng, weight 0–1)`.
    - `calls: collections.Counter` — incremented per method call, keyed by method name (`"travel_times"` counts one per origin×dest element).
- Produces (`fake.py`): `FakeProvider()` implementing `Provider`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_fake_provider.py`

```python
from backend.app.data.cities import CITIES, PREFS
from backend.app.providers.fake import FakeProvider
from backend.app.geo import distance_m

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
    import pytest
    c = CITIES["capetown"]
    with pytest.raises(ValueError):
        FakeProvider().travel_times(c, [(c.people[0], "transit")], [c.candidates[0].at])

def test_route_steps():
    c = CITIES["munich"]
    steps = FakeProvider().route(c, c.people[0], "transit", c.candidates[0].at)
    assert steps and steps[0].icon == "walk"
    assert all(s.text for s in steps)

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
    from backend.app.geo import LatLng
    mid = LatLng((s + n) / 2, (w + e) / 2)
    assert p.places(c, mid, 1500, "drinks") is not None

def test_heat_points():
    pts = FakeProvider().heat(CITIES["london"])
    assert len(pts) >= 50
    assert all(0 < w <= 1 for _, _, w in pts)
```

- [ ] **Step 2: Run** — `.venv/bin/pytest backend/tests/test_fake_provider.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `base.py`.**

- [ ] **Step 4: Implement `FakeProvider` in `fake.py`.** Decisions the tests don't pin:
  - Time model (km = straight-line km): transit `8 + km × 1.3 / 22 × 60`; bike `2 + km × 1.25 / 15 × 60`; car `6 + km × 1.4 / 25 × 60`; plus deterministic jitter in −2..+2 from `hashlib.sha256(f"{city.id}|{person.name}|{mode}|{dest.lat:.4f}|{dest.lng:.4f}")`; round; clamp to ≥ 3. Raise `ValueError` if mode not in `city.modes`.
  - Routes: transit → walk to a stop, one or two ride legs (icon `train`/`bus`/`tram`, generic line labels like "U-Bahn line", "Tube line", "Muni bus" chosen per city), walk at the end, minutes summing to the travel time; bike/car → one leg + an `info` step with distance.
  - Places: build a **city-wide pool once per city** (cache it): for every candidate area and heat centre, generate 6–10 places scattered 50–1200 m around it from the mockup's `FOOD`/`DRINKS` templates, using a `random.Random` seeded from `hashlib` of `(city.id, area name, kind)`; drop ~1/3 of types per area so mixes differ. `places()` filters the pool by kind and radius. Names may repeat across areas; append the area's short name if needed for uniqueness ("Sample Sushi Bar — Soho").
  - Heat: for each heat centre, ~10 × weight points scattered within 650 m, weight from the centre's weight.

- [ ] **Step 5: Run** — Expected: PASS.

- [ ] **Step 6: Commit** — `git add backend && git commit -m "feat: provider interface and deterministic fake provider"`

---

### Task 4: Ranking engine

**Files:**
- Create: `backend/app/engine.py`, `backend/tests/test_engine.py`

**Interfaces:**
- Consumes: `Provider`, `Place`, `City`, `LatLng`, `distance_m`, `PREFS`.
- Produces:
  - `FAIR_ZONE_MIN = 5`, `MAX_SPOTS = 3`
  - `@dataclass SpotResult(id: str, name: str, at: LatLng, times: list[int], longest: int, spread: int, in_fair_zone: bool, matching: int)` — `id` is the area name, or `"custom"`.
  - `@dataclass PlaceResult(place: Place, times: list[int], walk_min: int, distance_m: int)`
  - `@dataclass RankResult(spots: list[SpotResult], skipped: list[SpotResult], candidates: list[SpotResult], best_longest: int)`
  - `rank(provider, city, modes: list[str], kind: str, prefs: set[str], radius_m: int) -> RankResult`
  - `evaluate_spot(provider, city, modes, kind, prefs, radius_m, at: LatLng, best_longest: int, id="custom", name="Your spot") -> SpotResult`
  - `places_for(provider, city, modes, at: LatLng, kind, prefs, radius_m) -> list[PlaceResult]` — matching places only, per-person times via **one** `travel_times` call, sorted by `max(times)` then distance; `walk_min = max(1, round(distance_m / 80))`.

Ranking algorithm (not determined by signatures):
```
times = provider.travel_times(city, list(zip(city.people, modes)), [a.at for a in candidates])
for each candidate: longest = max(col), spread = longest - min(col)
best = min(longest); in_fair_zone = longest <= best + FAIR_ZONE_MIN
order = sorted(candidates, key=(longest, spread, name))
for s in order:
    if not s.in_fair_zone or len(spots) == MAX_SPOTS: break
    s.matching = count of places_for-style matches (pool filter only, no travel call)
    (spots if s.matching > 0 else skipped).append(s)
candidates = all, each with matching filled lazily (count only) for the "how picked" layer
```
A place "matches" when `place.kind == kind` and (`not prefs` or `place.type in prefs`).

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_engine.py`. Use a small `StubProvider` in the test file with hand-set times and places so fairness rules are pinned exactly:

```python
from backend.app import engine
from backend.app.data.cities import CITIES
from backend.app.providers.base import Place
from backend.app.geo import LatLng, offset
from collections import Counter

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
    assert [s.name for s in r.spots] == ["Glockenbachviertel", "Sendlinger Tor", "Gärtnerplatz"]
    # 17/1 spread vs 17/3 spread → Glockenbach first; Gärtnerplatz longest 17 spread 5 last
    assert r.best_longest == 17

def test_fair_zone_boundary_is_inclusive_5():
    city, p = make({"Sendlinger Tor": [10, 10, 10], "Gärtnerplatz": [15, 9, 9], "Glockenbachviertel": [16, 9, 9]},
                   {"Sendlinger Tor": ["Pizza"], "Gärtnerplatz": ["Pizza"], "Glockenbachviertel": ["Pizza"]})
    r = engine.rank(p, city, M, "food", set(), 800)
    assert [s.name for s in r.spots] == ["Sendlinger Tor", "Gärtnerplatz"]
    assert all(s.in_fair_zone for s in r.spots)

def test_spot_without_match_is_skipped_and_replaced_within_zone():
    city, p = make({"Sendlinger Tor": [10, 10, 10], "Gärtnerplatz": [11, 10, 10], "Glockenbachviertel": [12, 10, 10], "Maxvorstadt (Uni)": [13, 10, 10]},
                   {"Sendlinger Tor": ["Sushi"], "Gärtnerplatz": ["Pizza"], "Glockenbachviertel": ["Sushi"], "Maxvorstadt (Uni)": ["Sushi"]})
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
    assert len(engine.rank(p, city, M, "food", set(), 800).candidates) == len(city.candidates)
```

Add one test with the real `FakeProvider`: `places_for` returns per-person `times` of length 3, sorted by `max(times)`, only matching types, and costs exactly `len(city.people) × len(results)` travel-time elements.

- [ ] **Step 2: Run** — `.venv/bin/pytest backend/tests/test_engine.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `engine.py`** per the algorithm above.
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** — `git add backend && git commit -m "feat: fairness ranking engine"`

---

### Task 5: API endpoints and validation

**Files:**
- Create: `backend/app/schemas.py`, `backend/tests/test_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `engine.rank`, `engine.evaluate_spot`, `engine.places_for`, `FakeProvider`, `CITIES`, `PREFS`.
- Produces (HTTP, JSON; lat/lng as `{"lat":…, "lng":…}`):
  - `GET /api/cities` → `{"cities": [{"id","name","modes","default_mode","bounds":[s,w,n,e],"people":[{"name","area","at"}]}], "prefs": {"food": [...], "drinks": [...]}, "radius": {"min":300,"max":1500,"step":100,"default":800}}`
  - `POST /api/search` body `SearchRequest{city: str, modes: list[Mode] (1–8 items, must equal number of people), kind: "food"|"drinks", prefs: list[str] (⊆ PREFS[kind], max 8), radius_m: int (300–1500, multiple of 100), selected: str | None, custom: LatLng | None}` → `{"spots": [Spot], "skipped": [{"id","name"}], "custom": Spot | null, "selected": str | null, "places": [PlaceOut], "candidates": [{"name","at","over_best","matching"}]}` where `Spot = {"id","name","at","times","longest","spread","in_fair_zone","matching"}`, `PlaceOut = {"name","type","rating","price","at","times","walk_min"}`. `selected` resolves as: requested `"custom"` with `custom` given → custom; requested id among spots → it; else first spot; else null (then `places` is `[]`).
  - `GET /api/route?city=&person=<index>&mode=&lat=&lng=` → `{"steps": [{"icon","text"}]}`
  - `GET /api/heat?city=` → `{"points": [[lat, lng, weight], ...]}`
  - Validation errors → 422 with FastAPI's standard body; unknown city → 404.
- `create_app(provider: Provider | None = None)` — tests may inject a provider; default `FakeProvider()`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app

@pytest.fixture
def client():
    return TestClient(create_app())

def body(**kw):
    b = {"city": "munich", "modes": ["transit"] * 3, "kind": "food", "prefs": [], "radius_m": 800}
    b.update(kw); return b

def test_cities(client):
    j = client.get("/api/cities").json()
    assert [c["id"] for c in j["cities"]] == ["capetown", "munich", "sf", "london"]
    assert j["radius"] == {"min": 300, "max": 1500, "step": 100, "default": 800}

def test_search_returns_up_to_three_fair_spots_with_places(client):
    j = client.post("/api/search", json=body()).json()
    assert 1 <= len(j["spots"]) <= 3
    assert all(s["in_fair_zone"] and s["matching"] >= 1 for s in j["spots"])
    assert j["selected"] == j["spots"][0]["id"]
    assert j["places"] and all(len(p["times"]) == 3 for p in j["places"])

def test_search_selected_and_custom(client):
    j = client.post("/api/search", json=body(selected="custom", custom={"lat": 48.14, "lng": 11.57})).json()
    assert j["custom"]["id"] == "custom" and j["selected"] == "custom"

def test_search_rejects_transit_in_cape_town(client):
    assert client.post("/api/search", json=body(city="capetown")).status_code == 422

def test_custom_spot_outside_bounds_rejected(client):
    assert client.post("/api/search", json=body(custom={"lat": 0.0, "lng": 0.0})).status_code == 422

@pytest.mark.parametrize("bad", [
    {"radius_m": 250}, {"radius_m": 1600}, {"radius_m": 850},
    {"prefs": ["Sushi"], "kind": "drinks"}, {"prefs": ["Nonsense"]},
    {"modes": ["transit"] * 2}, {"modes": ["transit"] * 9}, {"modes": ["plane"] * 3},
])
def test_search_validation(client, bad):
    assert client.post("/api/search", json=body(**bad)).status_code == 422

def test_unknown_city_404(client):
    assert client.post("/api/search", json=body(city="paris")).status_code == 404

def test_route_and_heat(client):
    r = client.get("/api/route", params={"city": "london", "person": 0, "mode": "transit", "lat": 51.513, "lng": -0.135})
    assert r.status_code == 200 and r.json()["steps"]
    assert client.get("/api/route", params={"city": "london", "person": 5, "mode": "transit", "lat": 51.513, "lng": -0.135}).status_code == 422
    assert len(client.get("/api/heat", params={"city": "sf"}).json()["points"]) >= 50
```

- [ ] **Step 2: Run** — `.venv/bin/pytest backend/tests/test_api.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement `schemas.py`** (pydantic v2 models with `field_validator`/`model_validator` for the cross-field rules: prefs vs kind, modes count vs city people, mode allowed in city, custom inside bounds; city lookup raising 404 lives in the route handler before validation of city-dependent rules — implement those rules in the handler or with a validation context, builder's choice).
- [ ] **Step 4: Implement the routes in `main.py`.** Also mount `frontend/` at `/` with `StaticFiles(directory=..., html=True)` **after** the API routes, only if the folder exists.
- [ ] **Step 5: Run all tests** — `.venv/bin/pytest -v` — Expected: PASS.
- [ ] **Step 6: Commit** — `git add backend && git commit -m "feat: search, cities, route and heat API"`

---

### Task 6: Abuse protection (rate limits, body size, CORS)

**Files:**
- Create: `backend/tests/test_protection.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `create_app`.
- Produces: env-configurable settings read in `create_app`:
  - `RATE_LIMIT_SEARCH` default `"30/minute"`, `RATE_LIMIT_DEFAULT` default `"60/minute"`
  - `ALLOWED_ORIGINS` comma-separated, default `"http://localhost:8000,http://127.0.0.1:8000,https://jonobaker1998.github.io"`
  - `MAX_BODY_BYTES` default `10240` → 413 when exceeded
  - 429 body: `{"detail": "Too many requests — please slow down."}`
- The limiter keys on `request.client.host`; real IPs come from uvicorn's `--proxy-headers` (set in Task 8). The limiter is created inside `create_app` so each app (and test) gets fresh counters.

- [ ] **Step 1: Write the failing tests**

```python
from fastapi.testclient import TestClient
from backend.app.main import create_app

B = {"city": "munich", "modes": ["transit"] * 3, "kind": "food", "prefs": [], "radius_m": 800}

def test_search_rate_limited_at_30_per_minute():
    c = TestClient(create_app())
    codes = [c.post("/api/search", json=B).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429
    assert "slow down" in c.post("/api/search", json=B).json()["detail"]

import httpx, pytest

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_rate_limit_is_per_client():
    app = create_app()
    def client(ip):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 1000)), base_url="http://t")
    async with client("1.1.1.1") as a, client("2.2.2.2") as b:
        for _ in range(30):
            await a.post("/api/search", json=B)
        assert (await a.post("/api/search", json=B)).status_code == 429
        assert (await b.post("/api/search", json=B)).status_code == 200

def test_rate_limit_uses_forwarded_for():
    # Mirrors Render: uvicorn with proxy headers sets client.host from X-Forwarded-For.
    # Here we assert the limiter key function reads request.client.host (not a header we trust blindly).
    from backend.app.main import client_key
    class R: client = type("C", (), {"host": "9.9.9.9"})(); headers = {"x-forwarded-for": "6.6.6.6"}
    assert client_key(R()) == "9.9.9.9"

def test_body_too_large():
    c = TestClient(create_app())
    big = dict(B, prefs=["x" * 20000])
    assert c.post("/api/search", json=big).status_code == 413

def test_cors_allows_pages_origin_only():
    c = TestClient(create_app())
    ok = c.options("/api/search", headers={"Origin": "https://jonobaker1998.github.io", "Access-Control-Request-Method": "POST"})
    bad = c.options("/api/search", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://jonobaker1998.github.io"
    assert "access-control-allow-origin" not in bad.headers
```

- [ ] **Step 2: Run** — `.venv/bin/pytest backend/tests/test_protection.py -v` — Expected: FAIL.
- [ ] **Step 3: Implement** in `main.py`: `client_key(request) -> str` (returns `request.client.host`), slowapi `Limiter(key_func=client_key)` with `@limiter.limit(...)` on each route, custom 429 handler, a small middleware rejecting `Content-Length` > `MAX_BODY_BYTES` (and bodies that turn out larger) with 413, `CORSMiddleware(allow_origins=..., allow_methods=["GET","POST"], allow_headers=["Content-Type"])`. Note: the existing API tests now share counters within one app — they each create their own client/app, so they stay under limits.
- [ ] **Step 4: Run all tests** — `.venv/bin/pytest -v` — Expected: PASS.
- [ ] **Step 5: Commit** — `git add backend && git commit -m "feat: rate limits, body size limit and CORS"`

---

### Task 7: Website

**Files:**
- Create: `frontend/index.html`, `frontend/styles.css`, `frontend/js/config.js`, `frontend/js/api.js`, `frontend/js/state.js`, `frontend/js/map.js`, `frontend/js/panel.js`, `frontend/js/app.js`

**Interfaces:**
- Consumes: the HTTP API from Task 5 (exact shapes there) and the 429 body from Task 6.
- Produces:
  - `config.js`: `export const API_BASE` — `""` unless `location.hostname.endsWith("github.io")`, then the Render URL constant `RENDER_URL` (placeholder `"https://meeting-in-the-middle-api.onrender.com"`, confirmed in Task 8).
  - `api.js`: `getCities()`, `search(req)`, `getRoute(params)`, `getHeat(city)` — each returns parsed JSON or throws `ApiError{status, message}`; calls `onSlow(true/false)` when a request has been pending > 3 s (drives the "Waking up the server…" banner).
  - `state.js`: `state` object (`city, modes[], kind, prefs:Set, radius, selected, custom, open, showHeat, showHow`) and `debounce(fn, ms)`.
  - `map.js`: `initMap(el)`, `drawResult(state, city, result, handlers)`, `drawHeat(points)`, `clearHeat()`; handlers `{onSelectSpot(id), onDragEnd(lat,lng), onPlaceHover(i,on), onPlaceClick(i)}`.
  - `panel.js`: `renderPanel(state, city, citiesData, result, handlers)`.

Port the layout, styling and behaviours from `.superpowers/brainstorm/mockups/layout-v4.html`, replacing every hard-coded number with API data. Behaviour checklist (each item is a manual check in Step 3):

- [ ] **Step 1: Build the files.** Rules:
  - Every state change calls `search` through `debounce(…, 300)`; the radius slider updates its label instantly but searches debounced; dragging only searches on drag end.
  - Route panel calls `/api/route` when a person is expanded (cache per person+mode+spot).
  - Heat layer fetched once per city when toggled on.
  - City without `transit` in `modes`: transit buttons disabled with the tooltip "Public transport data is too patchy here".
  - Empty top list → panel text "Nothing matches near a fair spot — try fewer preferences or a bigger radius."; skipped line "Skipped A, B — no <prefs> <restaurants|bars> there".
  - 429 → non-blocking banner "Too many requests — please slow down." for 10 s; other errors → banner "Something went wrong — try again."
  - Pending > 3 s → banner "Waking up the server… this can take up to a minute the first time."
  - "Demo data" tag visible in the header.
  - Leaflet 1.9.4 CSS/JS from unpkg as in the mockup; JS loaded as `<script type="module" src="js/app.js">`.

- [ ] **Step 2: Run locally** — `.venv/bin/uvicorn backend.app.main:app --reload`, open http://localhost:8000.

- [ ] **Step 3: Manual check, each city** (tick all):
  - Switching city resets modes to the city default and refits the map; Cape Town shows transit disabled.
  - Group mode switch and per-person mode icons both change times and can reorder the spots.
  - Clicking a person expands route steps and highlights their line.
  - Restaurants/Bars toggle resets preference chips; chips filter places and can cause a skipped line.
  - Selecting Steak + only drinks-like combos that match nothing shows the empty state (no errors in the console).
  - Clicking a numbered spot on the map or its card selects it; dragging the selected spot creates "Your spot" with stats; × removes it.
  - Each place shows per-person chips; list is fairest-first; hover enlarges its pin; click zooms.
  - Heat and "how picked" toggles draw and clear.
  - Dragging the radius slider quickly sends ≤ 1 request per pause (check the Network tab).
  - Stop the server and click something → error banner, page doesn't break.

- [ ] **Step 4: Commit** — `git add frontend && git commit -m "feat: website wired to the API"`

---

### Task 8: Deploy (Render + GitHub Pages) and docs

**Files:**
- Create: `render.yaml`, `.github/workflows/pages.yml`
- Modify: `frontend/js/config.js` (real Render URL), `README.md`

**Interfaces:**
- Consumes: `backend.app.main:app`, `frontend/`.
- Produces: live API on Render, live site at `https://jonobaker1998.github.io/meeting_in_the_middle/`.

- [ ] **Step 1: Write `render.yaml`** — one `web` service: `runtime: python`, `plan: free`, `buildCommand: pip install -r requirements.txt`, `startCommand: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`, `healthCheckPath: /api/health`, env `PYTHON_VERSION=3.12.8`, `ALLOWED_ORIGINS=https://jonobaker1998.github.io`.

- [ ] **Step 2: Write `.github/workflows/pages.yml`** — on push to `main` (paths `frontend/**`) and `workflow_dispatch`: `actions/checkout@v4`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` with `path: frontend`, `actions/deploy-pages@v4`; permissions `pages: write`, `id-token: write`, `contents: read`.

- [ ] **Step 3: README "Deploy" section** listing the **owner-only steps**, in order:
  1. GitHub → repo Settings → General → Danger Zone → Change visibility → Public.
  2. GitHub → Settings → Pages → Source: "GitHub Actions".
  3. Render → sign up (free) → New → Blueprint → pick this repo → Apply. Keep the free instance type. Note the service URL.
  4. Tell Claude the Render URL (to put in `config.js`), merge to `main`.
  Also confirm GitHub secret scanning / push protection is on (Settings → Code security).

- [ ] **Step 4: Owner does steps 1–3** (pause and wait for the Render URL).

- [ ] **Step 5: Set `RENDER_URL` in `config.js`**, commit, push, merge to `main`.

- [ ] **Step 6: Verify live**
  - `curl -s https://<render-url>/api/health` → `{"status":"ok"}` (may take ~60 s on first call).
  - Open `https://jonobaker1998.github.io/meeting_in_the_middle/` → map loads, wake-up banner appears then clears, search works for all four cities.
  - `for i in $(seq 31); do curl -s -o /dev/null -w "%{http_code}\n" -X POST https://<render-url>/api/search -H 'Content-Type: application/json' -d '{"city":"munich","modes":["transit","transit","transit"],"kind":"food","prefs":[],"radius_m":800}'; done | sort | uniq -c` → 30 × `200`, 1 × `429`.

- [ ] **Step 7: Commit** — `git add render.yaml .github README.md frontend/js/config.js && git commit -m "chore: deploy to Render and GitHub Pages"`
