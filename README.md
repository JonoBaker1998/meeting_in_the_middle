# meeting_in_the_middle
App to determine where to meet to keep everyone happy

A website that finds the **fairest** place for a group to meet — nobody travels much longer than anyone else — and shows restaurants and bars nearby. This proof of concept runs on demo data for Cape Town, Munich, San Francisco and London.

## Run locally

One-time setup (no admin rights needed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements-dev.txt
```

Start the app, then open http://localhost:8000:

```bash
.venv/bin/uvicorn backend.app.main:app --reload
```

Run the tests:

```bash
.venv/bin/pytest
```

## Deploy (free)

The website goes on **GitHub Pages** and the Python API on **Render's free plan**.
Render's free plan sleeps when idle, so the first visit after a while takes 30–60 seconds
(the site shows "Waking up the server…").

Owner-only steps, in order:

1. **Make the repo public:** GitHub → this repo → Settings → General → Danger Zone → Change visibility → Public.
2. **Check secret protection is on:** Settings → Code security → Secret scanning and Push protection → Enabled.
3. **Turn on Pages:** Settings → Pages → Source: **GitHub Actions**.
4. **Create the API on Render:** sign up at render.com (free) → New → Blueprint → pick this repo → Apply.
   Keep the **Free** instance type. Copy the service URL (e.g. `https://meeting-in-the-middle-api.onrender.com`).
5. If the URL differs from the one in `frontend/js/config.js` (`RENDER_URL`), update it there.
6. Merge to `main`. The Pages workflow publishes `frontend/` to
   `https://jonobaker1998.github.io/meeting_in_the_middle/`.

### Abuse protection

- Search is limited to 30 requests per minute per visitor (other endpoints 60/minute); excess gets HTTP 429.
- Requests over 10 KB are rejected (413); inputs are validated (max 8 people, radius 300–1500 m, known preferences, points inside the city).
- Only the Pages site and localhost may call the API from a browser (CORS).
- No secrets are stored in this repo, and both hosts are on free plans that cannot bill.

Settings can be changed with environment variables on Render: `RATE_LIMIT_SEARCH`, `RATE_LIMIT_DEFAULT`,
`ALLOWED_ORIGINS`, `MAX_BODY_BYTES`.
