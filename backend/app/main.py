"""FastAPI application: JSON API for Meet in the Middle, plus the static website."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Meet in the Middle")

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
