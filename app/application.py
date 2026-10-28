"""Application startup: builds the FastAPI app and connects its parts together.

create_app() is a factory function. Tests call it with their own settings, so
they never touch the real data folder or need an API key.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import APP_VERSION, PROJECT_ROOT, Settings, load_settings
from app.errors import AppError
from app.llm import build_answerer
from app.retrieval import KeywordRetriever
from app.routes import api_router
from app.storage import DocumentStore

STATIC_DIR = PROJECT_ROOT / "static"


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    """Turn any expected AppError into a JSON response with the right status code."""
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    store = DocumentStore(settings.database_path)
    store.initialize()

    app = FastAPI(
        title="DocuMind",
        version=APP_VERSION,
        description="Upload PDF or TXT documents and ask questions about them.",
    )
    # app.state is FastAPI's place for shared objects. The routes read them through Depends().
    app.state.settings = settings
    app.state.store = store
    app.state.retriever = KeywordRetriever()
    app.state.answerer = build_answerer(settings)

    app.add_exception_handler(AppError, handle_app_error)
    app.include_router(api_router)

    # The web page is served last, so /api routes always match first.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
