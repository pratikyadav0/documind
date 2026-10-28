"""Configuration: settings come from environment variables and an optional .env file.

Why environment variables? Secrets such as ANTHROPIC_API_KEY must never be
written into the code. The .env file is for local development only and is
excluded from Git by .gitignore.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

APP_VERSION = "0.1.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "documind.db"

# .env.example ships with this placeholder. Treating it as "no key" means a
# freshly copied .env falls back to demo mode instead of calling Claude with a fake key.
PLACEHOLDER_API_KEYS = {"", "your-anthropic-api-key-here"}


class Settings(BaseModel):
    """All runtime settings in one place. The defaults are safe for local development."""

    anthropic_api_key: str = ""
    anthropic_model: str = DEFAULT_MODEL
    demo_mode: bool = False
    anthropic_timeout_seconds: float = 30.0
    max_upload_mb: float = 5.0
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 4
    database_path: Path = DEFAULT_DATABASE_PATH
    log_level: str = "INFO"

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def use_demo_responses(self) -> bool:
        """Demo answers are used when demo mode is forced on, or when no API key is set."""
        return self.demo_mode or not self.anthropic_api_key


def _parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _read_number(name: str, default: str, cast: type[int] | type[float]) -> int | float:
    """Read a number from the environment and say which variable is wrong if it is not a number."""
    raw_value = os.getenv(name, default).strip() or default
    try:
        return cast(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number, but it was set to '{raw_value}'.") from error


def load_settings() -> Settings:
    """Read settings from the environment. Raises ValueError for impossible combinations."""
    # load_dotenv never overwrites a variable that is already set in the shell.
    load_dotenv(PROJECT_ROOT / ".env")

    raw_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    api_key = "" if raw_key in PLACEHOLDER_API_KEYS else raw_key

    database_raw = os.getenv("DATABASE_PATH", "").strip()
    database_path = Path(database_raw) if database_raw else DEFAULT_DATABASE_PATH
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    settings = Settings(
        anthropic_api_key=api_key,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        demo_mode=_parse_bool(os.getenv("DEMO_MODE"), default=False),
        anthropic_timeout_seconds=_read_number("ANTHROPIC_TIMEOUT_SECONDS", "30", float),
        max_upload_mb=_read_number("MAX_UPLOAD_MB", "5", float),
        chunk_size=_read_number("CHUNK_SIZE", "800", int),
        chunk_overlap=_read_number("CHUNK_OVERLAP", "150", int),
        top_k=_read_number("TOP_K", "4", int),
        database_path=database_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )

    if settings.chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than 0.")
    if settings.chunk_overlap < 0 or settings.chunk_overlap >= settings.chunk_size:
        raise ValueError("CHUNK_OVERLAP must be 0 or more and smaller than CHUNK_SIZE.")
    return settings
