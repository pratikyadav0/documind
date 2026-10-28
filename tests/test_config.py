"""Tests for loading settings from environment variables."""

import pytest

from app.config import Settings, load_settings


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "ANTHROPIC_API_KEY", "DEMO_MODE", "CHUNK_SIZE", "CHUNK_OVERLAP", "DATABASE_PATH", "MAX_UPLOAD_MB",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_placeholder_api_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "your-anthropic-api-key-here")
    settings = load_settings()
    assert settings.anthropic_api_key == ""
    assert settings.use_demo_responses is True


def test_real_looking_key_enables_claude_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-value")
    settings = load_settings()
    assert settings.anthropic_api_key == "test-key-value"
    assert settings.use_demo_responses is False


def test_demo_mode_is_forced_on_by_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-value")
    monkeypatch.setenv("DEMO_MODE", "true")
    assert load_settings().use_demo_responses is True


def test_overlap_not_smaller_than_chunk_size_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    with pytest.raises(ValueError):
        load_settings()


def test_relative_database_path_is_resolved_from_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", "custom/folder/test.db")
    settings = load_settings()
    assert settings.database_path.is_absolute()
    assert settings.database_path.name == "test.db"


def test_max_upload_bytes_converts_megabytes() -> None:
    assert Settings(max_upload_mb=1).max_upload_bytes == 1024 * 1024


def test_invalid_number_error_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("CHUNK_SIZE", "eight hundred")
    with pytest.raises(ValueError, match="CHUNK_SIZE must be a number"):
        load_settings()


def test_missing_env_file_and_no_key_still_gives_demo_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    # Works even if there is no .env file: every setting has a safe default.
    _clear_env(monkeypatch)
    monkeypatch.setenv("DATABASE_PATH", "data/test-only.db")
    settings = load_settings()
    assert settings.use_demo_responses is True
    assert settings.max_upload_mb == 5.0


def test_env_example_model_matches_the_code_default() -> None:
    # The model name must agree in three places: the code default, .env.example, and the docs.
    from pathlib import Path

    from app.config import DEFAULT_MODEL

    example_path = Path(__file__).resolve().parent.parent / ".env.example"
    lines = example_path.read_text(encoding="utf-8").splitlines()
    model_lines = [line for line in lines if line.startswith("ANTHROPIC_MODEL=")]
    assert model_lines == [f"ANTHROPIC_MODEL={DEFAULT_MODEL}"]
