# Meet in the Middle — Proof of Concept Design

Date: 2026-11-24
Status: approved 2026-11-24 (London added at approval)

## 1. Intent

A small group of friends in different parts of a city wants to meet for food or
drinks. Today someone picks a place and somebody ends up travelling 50 minutes
while everyone else takes 10. This app finds the spot that is **fairest** to
reach for everyone — nobody travels much longer than anyone else — and then
shows good restaurants or bars around it.

The repo's own one-liner: "App to determine where to meet to keep everyone
happy."

The long-term product is a website and later an iPhone app. This document
covers the **proof of concept (PoC)**: the website, backed by a Python server,
running on fake but realistic data for four cities.

## 2. Goals, non-goals, anti-goals

### Goals (PoC)
- A website that reproduces the approved mockup
  (`.superpowers/brainstorm/mockups/layout-v4.html`) driven by a real Python
  backend instead of hard-coded numbers.
- The fairness logic, hotspot ranking, preference handling and "your spot"
  drag all computed by the backend.
- Four demo cities: **Cape Town**, **Munich**, **San Francisco**, **London**,
  each with three pre-set people.
- A data-provider seam so the fake data can later be swapped for Google Maps
  Platform without changing the ranking logic or the website.
- Live online at zero cost, with basic abuse protection (see §7).

### Non-goals (PoC)
- Entering or detecting people's locations (people are pre-set per city;
  "+ Add person" stays a disabled placeholder).
- Real Google / TravelTime calls, API keys or billing.
- User accounts, saving searches, sharing links.
- The iPhone app.
- Security beyond §7.1 (no logins or personal data exist yet).

### Anti-goals (would be a failure even if it works)
- Recommending an area with nothing matching what the group asked for.
- Showing a spot as "fairest" when it is not — the numbers on screen must be
  the numbers the ranking used.
- A design where a future API key would have to live in the browser.
- A design where one search could quietly cost real money (relevant from
  phase 2; the provider seam must make call counts visible).

## 3. Constraints

- **Language:** backend in Python (the owner's strongest language).
- **No Node.js** on the owner's machine; the PoC must not need it.
- **Local Python is 3.7.6 (Anaconda)** — too old for current FastAPI. The
  build installs Python 3.12 (Homebrew) and uses a project virtual
  environment; Anaconda stays untouched.
- **GitHub Pages serves static files only** — it cannot run Python. Pages on a
  free account requires the repo to be public.
- **Cape Town has no public-transport option** — the owner decided transport
  data there is too patchy. Cape Town offers bike and car only; car is the
  default.
- Repo: `git@github.com:JonoBaker1998/meeting_in_the_middle.git`, branch
  `main`, currently only README, LICENSE and a Python `.gitignore`.

## 4. Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | Python **FastAPI** backend + **plain HTML/CSS/JavaScript** website with **Leaflet** maps | No build tools, no Node; the approved mockup becomes the website almost directly. Plain JS can get messy if the website grows a lot — can move to React later. |
| B | FastAPI backend + **React/TypeScript** website | More structure and an easier path to React Native for iPhone, but needs Node and a frontend toolchain before anything works. Too much overhead for a PoC. |
| C (rejected) | All-Python UI (**Streamlit/NiceGUI**) | No JavaScript, but dragging the spot and clickable map markers fight these frameworks, they can't be hosted on GitHub Pages, and there's no route to an iPhone app. |

The owner picked **A**.

iPhone path for A (later, not in this PoC): first "Add to Home Screen" as a web
app, then wrap with Capacitor for the App Store. The Python API is reused
unchanged.

## 5. What the owner decided (product behaviour)

These come from the mockup sessions and are fixed for the PoC.

### 5.1 Fairness
- The fairest spot is the one where **the longest anyone travels is as short as
  possible**.
- Ties are broken by **spread** (longest minus shortest trip): smaller spread
  wins.
- The **fair zone** is every candidate spot whose longest trip is within
  **5 minutes** of the best possible longest trip.

### 5.2 Finding the top 3 spots
1. Compute every person's travel time to every candidate spot.
2. Rank candidates by fairness (longest trip, then spread).
3. A spot only qualifies if it has **at least one place matching the current
   food/drink type and preferences** within the radius. Spots with no match
   are skipped and the next-fairest takes their place — **but only from inside
   the fair zone** (owner agreed: "as long as it's still in the fair zone").
   A spot outside the fair zone is never shown in the top list.
4. Show up to 3 qualifying spots. If fewer than 3 qualify, show fewer. If none
   qualify, show an empty state ("Nothing matches near a fair spot — try fewer
   preferences or a bigger radius"). The UI lists any skipped spots ("Skipped
   Gärtnerplatz — no Sushi there").
5. "Your spot" (dragged) is exempt: it is always shown with its real stats,
   even if it is outside the fair zone or has no matches.

### 5.3 Travel modes
- Modes: **public transport, bike, car**.
- An "everyone travels by" group switch sets all people at once.
- **Each person can override their own mode** (mixed groups are normal).
- Changing any mode re-runs the ranking.

### 5.4 People panel
- Each person shows their name, area, mode icons and minutes to the selected
  spot.
- Clicking a person expands **their step-by-step route** to the selected spot
  and highlights their line on the map.

### 5.5 Places
- Toggle **Restaurants / Bars**.
- **Preference chips** (multi-select; none selected = everything):
  - Food: Asian, Sushi, Burgers, Italian, Pizza, Mexican, Vegetarian, Steak
  - Drinks: Cocktails, Wine, Craft beer, Rooftop, Pub
- **Radius slider**: 300–1500 m, step 100, default 800 m, centred on the
  selected spot.
- Each place shows name, type, price level, rating, walk time from the spot,
  and **each person's travel time to that place** (coloured chips).
- List sorted **fairest first** (by longest per-person time to the place).
- Hovering a place enlarges its map pin; clicking zooms to it.

### 5.6 Map
- People as coloured initials with dashed lines to the selected spot.
- Top 3 spots as numbered circles; click one to select it.
- The selected spot is **draggable**. Dropping it creates a **"Your spot"**
  card with the same stats (longest trip, spread, matching places) and its own
  places list. It can be removed with ×.
- Optional layer: **"Show where the top-rated places are"** — a heat-style glow
  over clusters of highly rated places across the city, including popular
  areas that are not fair for this group.
- Optional layer: **"Show how these were picked"** — candidate spots coloured
  green (fair zone) / amber / red, sized by how many good places are nearby.

### 5.7 Demo content
- Cities and people as in the mockup:
  - **Cape Town** (car default, no transit): Alex — Sea Point, Sam —
    Observatory, Jo — Claremont.
  - **Munich** (transit default): Alex — Schwabing, Sam — Sendling, Jo —
    Haidhausen.
  - **San Francisco** (transit default): Alex — Mission, Sam — Inner
    Richmond, Jo — North Beach.
  - **London** (transit default; added after the mockup): Alex — Camden,
    Sam — Brixton, Jo — Hammersmith. Candidate areas include e.g. Soho,
    Covent Garden, Southbank / Waterloo, Shoreditch, Victoria, Clapham,
    Islington, Kensington.
- Places are clearly fake ("Sample …") and the UI keeps a visible "demo data"
  label.
- "Reproduce the mockup" means **the same layout and behaviour**, not the same
  numbers. The mockup's minutes were hand-written; the fake data model will
  produce its own, and which area ranks first may differ. No per-area
  override tables are needed.

## 6. How it's built

### 6.1 Shape

```
browser (HTML/JS + Leaflet)  ──HTTP/JSON──>  FastAPI app
                                               ├── engine (fairness, ranking, prefs)
                                               └── provider (interface)
                                                     ├── FakeProvider   ← PoC
                                                     └── GoogleProvider ← phase 2
```

FastAPI serves both the JSON API and the website's static files, so locally
it's one command and one URL.

### 6.2 Provider interface (the seam for real data later)

Four operations; the engine only ever talks to these:

- `travel_times(people, spots) -> minutes[person][spot]` — each person uses
  their own mode.
- `route(person, spot) -> list of steps` — step text plus an optional icon
  (walk / train / bus / bike / car).
- `places(centre, radius, kind) -> list of places` — name, type/category,
  rating, price level, location.
- `top_rated_areas(city) -> weighted points` — for the heat layer.

Every provider call is counted per request so phase 2 can show and cap API
usage.

### 6.3 FakeProvider
- **Travel times** derived from straight-line distance and a per-mode model
  (rough speeds plus fixed overhead for walking to a stop / parking), with
  small deterministic per-person-per-spot variation so the results look real
  but are repeatable. Exact speeds and overheads are the builder's call;
  results should land in plausible city ranges (roughly 10–40 minutes for the
  demo people).
- **Routes**: generated steps in the mockup's style ("🚶 Walk 4 min to …",
  "🚇 U6 · 5 stops", "Cycle via …"). Realistic line names are nice-to-have,
  not required.
- **Places**: generated deterministically per area from the mockup's
  templates (name, type, rating, price), so each area has a different mix and
  some areas lack some cuisines — this is what makes the "skipped" behaviour
  observable.
- **Top-rated areas**: per-city weighted points, including at least one
  popular-but-unfair area per city.

### 6.4 Candidate spots
- In the PoC each city has a fixed list of **named candidate areas**
  (roughly 8–12 per city, including the four from the mockup). Named areas
  give readable spot names for free.
- "Your spot" (dragged) is evaluated the same way as any candidate, on demand.
- Phase 2 replaces this with a grid over the area between people plus nearby
  transit stations, named by reverse lookup.

### 6.5 API (shape, not final field names)
- `GET /api/cities` → cities, their people, default and allowed modes, the
  preference lists.
- `POST /api/search` with city, each person's mode, kind (food/drinks),
  preferences, radius, optional custom spot → top 3 spots (with stats),
  skipped spots, per-person times, and places for the selected spot including
  per-person times to each place.
- `GET /api/route` for one person to one spot.
- `GET /api/heat?city=…` → weighted points.
- Optionally `GET /api/candidates` for the "how these were picked" layer.

### 6.6 Website
- Static files: `index.html`, `styles.css`, and a few JS modules (API calls,
  map drawing, side panel). Leaflet loaded from a CDN; OpenStreetMap tiles.
- One base URL setting for the API, so the same files work locally and when
  the frontend is hosted on GitHub Pages.

### 6.7 Suggested repo layout (builder may adjust)

```
backend/
  app/
    main.py          # FastAPI app, routes, serves frontend/
    engine.py        # fairness, fair zone, ranking, preference skipping
    models.py        # request/response models
    providers/
      base.py        # provider interface
      fake.py        # FakeProvider
    data/cities.py   # demo cities, people, candidate areas, heat points
  tests/
frontend/
  index.html
  styles.css
  js/
requirements.txt
```

### 6.8 Testing
- Unit tests (pytest) for the engine: longest-trip ranking, spread tie-break,
  fair zone boundary, skipping spots with no matching places, mixed modes,
  Cape Town rejecting transit.
- API tests with FastAPI's test client for each endpoint.
- The website is checked by hand against the mockup.

## 7. Hosting (in scope — owner decided to go public)

- **Local**: `uvicorn` serves API + website at one URL.
- **Online (£0)**: website on **GitHub Pages**, Python API on **Render's free
  plan**. The repo becomes **public** (required for free Pages).
- Render's free tier sleeps when idle; the first request after a while takes
  ~30–60 s. The website shows a friendly "waking up the server…" state while
  the first request is pending, and does not fire a request on every radius
  slider tick (debounce).
- Needs CORS configured so the API accepts calls from the Pages origin (and
  localhost for development).
- Owner-only steps the plan must call out: make the repo public, create the
  Render account (free plan; check at sign-up whether a payment method is
  required, and keep the service on the free instance type), turn on Pages.
- Deploy: Render builds from the repo; Pages publishes the `frontend/` folder
  (via a GitHub Actions workflow or Pages source folder — builder's call).

### 7.1 Protection against abuse (owner requirement)

Owner's concern: not being taken advantage of by DDoS or spam.

**PoC position:** there is nothing paid behind the site, so an attack cannot
cost money. Worst case, the demo is slow or down until the attack stops.
That is accepted for the PoC. Protections still built in:

- **No secrets anywhere in the repo or the browser.** `.env` stays
  git-ignored; GitHub's secret scanning / push protection stays on.
- **Rate limiting per IP** on every API endpoint (e.g. ~30 requests/minute
  per IP for search, stricter if abused), returning HTTP 429. The website
  handles 429 with a "slow down" message.
- **Input limits** validated server-side: max people (e.g. 8), radius within
  300–1500 m, preference lists only from the known values, coordinates
  within the selected city's bounds, small max request body size.
- **CORS limited** to the Pages site and localhost. (This stops other
  websites embedding the API, not scripts — rate limiting covers those.)
- **Free plans only**: neither GitHub Pages nor Render's free plan can
  auto-scale into a bill.
- **GitHub Pages** is served from GitHub's CDN, which absorbs heavy traffic
  for the static site.

**Phase 2 additions (before any Google key goes live) — recorded now:**

- API key only in the Render environment, never in the repo or browser;
  restricted in Google Cloud to only the Routes and Places APIs.
- **Hard daily quotas** set in Google Cloud for each API, plus **budget
  alerts** — so a flood of requests hits a quota wall, not a bill.
- A server-side **daily call budget** (counted via the provider seam, §6.2):
  once spent, the app falls back to "demo data" or "try again tomorrow".
- **Caching** of travel times and places so repeat searches cost nothing.
- Optional: a bot check (e.g. Cloudflare Turnstile, free) on search, and
  Cloudflare in front of the API if a custom domain is added.

## 8. Phase 2 (not in this PoC, recorded so the PoC doesn't block it)
- GoogleProvider: Routes API Compute Route Matrix for times, Compute Routes
  for step-by-step routes, Places API Nearby Search for places.
- Rough free allowances checked 2026-11-24: Route Matrix ~10,000 elements/month
  free at Essentials (~$5/1,000 after), possibly the Pro tier for transit
  (~5,000 free, ~$10/1,000) — confirm before switching on. Nearby Search (Pro)
  5,000/month free, then ~$32/1,000. One search with 3 people × 25 candidates
  ≈ 75 matrix elements, so ~100 searches/month free.
- Caching and a per-day call cap so costs can't run away.
- Entering locations (address search / "use my location").
- iPhone: home-screen web app, then Capacitor wrapper.

## 9. Calls made on the owner's behalf (please check)
- Tie-break by spread; fair zone = within 5 minutes of the best.
- A spot needs ≥1 matching place to qualify; fewer than 3 qualifying → show
  fewer; none → empty state.
- Demo matches the mockup's layout and behaviour, not its hand-written numbers.
- Candidate spots are a fixed named list per city in the PoC.
- Online hosting = GitHub Pages (website) + Render free tier (Python API);
  owner decided it goes public in this build.
- Abuse protection level for the PoC: rate limits + input limits + CORS +
  free plans only; full DDoS shielding (Cloudflare) deferred to phase 2.
- Rate limit ~30 search requests/minute per IP; max 8 people.
- Python 3.12 via Homebrew in a project virtual environment.
- Mockup files in `.superpowers/` are added to `.gitignore`.

## 10. Left to the builder
- Exact fake-data formulas, speeds, jitter, place templates per area.
- Exact API field names and JS module split.
- Visual polish beyond the mockup.
