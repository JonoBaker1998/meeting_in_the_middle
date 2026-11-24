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
