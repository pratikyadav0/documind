"""Checks that the browser code calls API routes that the server really provides.

A "contract" test: if someone renames a route on one side only, this test fails.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

APP_JS = Path(__file__).resolve().parent.parent / "static" / "app.js"


def find_frontend_api_paths() -> set[str]:
    """Return every path the browser passes to callApi(), with ${...} turned into {name}."""
    source = APP_JS.read_text(encoding="utf-8")
    raw_paths = re.findall(r"callApi\(\s*[`\"]([^`\"]+)[`\"]", source)
    return {re.sub(r"\$\{[^}]+\}", "{id}", path) for path in raw_paths}


def test_every_frontend_call_matches_a_backend_route(client: TestClient) -> None:
    backend_paths = set(client.app.openapi()["paths"].keys())
    frontend_paths = find_frontend_api_paths()
    assert frontend_paths, "the frontend should call at least one API route"
    for frontend_path in frontend_paths:
        full_path = "/api" + frontend_path
        assert full_path in backend_paths or full_path.replace("{id}", "{document_id}") in backend_paths, (
            f"frontend calls {full_path}, but the backend has no such route"
        )


def test_frontend_uses_the_upload_limit_and_mode_fields_from_health(client: TestClient) -> None:
    health = client.get("/api/health").json()
    source = APP_JS.read_text(encoding="utf-8")
    assert "max_upload_mb" in health
    assert "health.max_upload_mb" in source
    assert "health.mode" in source
    assert "health.model" in source


def test_frontend_renders_document_text_safely() -> None:
    source = APP_JS.read_text(encoding="utf-8")
    # Untrusted text must go through textContent. Assigning to innerHTML would let a document inject markup.
    # We look for an actual assignment, so a comment that mentions innerHTML does not fail the test.
    assert re.search(r"\.innerHTML\s*=", source) is None
    assert "textContent" in source
