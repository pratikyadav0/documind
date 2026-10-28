"""Endpoint tests: they exercise the whole API through FastAPI's TestClient."""

import anthropic
import httpx
from fastapi.testclient import TestClient

from app.application import create_app
from app.config import Settings
from app.llm import INSUFFICIENT_EVIDENCE_MESSAGE, ClaudeAnswerer
from tests.fakes import FakeClient, FakeMessages, text_response

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def upload_text(client: TestClient, text: str, name: str = "handbook.txt"):
    return client.post("/api/documents", files={"file": (name, text.encode("utf-8"), "text/plain")})


def test_health_reports_demo_mode(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] == "demo"


def test_upload_text_returns_201_and_a_summary(client: TestClient) -> None:
    response = upload_text(client, "Vacation: 18 days per year. Remote work is allowed.")
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "handbook.txt"
    assert body["file_type"] == "txt"
    assert body["chunk_count"] >= 1
    assert body["readable_pages"] is None
    assert "file" not in body  # the original file content is never returned


def test_upload_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post("/api/documents", files={"file": ("photo.png", b"data", "image/png")})
    assert response.status_code == 415
    assert "detail" in response.json()


def test_upload_rejects_empty_file(client: TestClient) -> None:
    response = upload_text(client, "")
    assert response.status_code == 400


def test_upload_rejects_file_over_the_limit(client: TestClient) -> None:
    response = upload_text(client, "x" * 20_000)
    assert response.status_code == 413


def test_upload_rejects_fake_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/documents", files={"file": ("fake.pdf", b"just text", "application/pdf")}
    )
    assert response.status_code == 415


def test_sample_document_is_listed_after_upload(client: TestClient, sample_text: str) -> None:
    upload_text(client, sample_text, name="synthetic_company_handbook.txt")
    documents = client.get("/api/documents").json()["documents"]
    assert len(documents) == 1
    assert documents[0]["filename"] == "synthetic_company_handbook.txt"


def test_ask_before_any_upload_returns_404(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "How many vacation days?"})
    assert response.status_code == 404


def test_ask_returns_demo_answer_with_sources(client: TestClient, sample_text: str) -> None:
    upload_text(client, sample_text, name="synthetic_company_handbook.txt")
    response = client.post("/api/ask", json={"question": "How many vacation days do employees get?"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "demo"
    assert body["insufficient_evidence"] is False
    assert "vacation" in body["answer"].lower()
    assert body["sources"]
    assert body["sources"][0]["label"] == "S1"
    assert body["sources"][0]["filename"] == "synthetic_company_handbook.txt"


def test_unrelated_question_reports_insufficient_evidence(client: TestClient, sample_text: str) -> None:
    upload_text(client, sample_text, name="synthetic_company_handbook.txt")
    response = client.post("/api/ask", json={"question": "What is the capital of Mongolia?"})
    body = response.json()
    assert response.status_code == 200
    assert body["insufficient_evidence"] is True
    assert body["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert body["sources"] == []


def test_question_that_is_too_short_is_rejected(client: TestClient, sample_text: str) -> None:
    upload_text(client, sample_text)
    response = client.post("/api/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_unknown_document_id_returns_404(client: TestClient, sample_text: str) -> None:
    upload_text(client, sample_text)
    response = client.post("/api/ask", json={"question": "vacation days", "document_ids": [999]})
    assert response.status_code == 404


def test_question_can_be_limited_to_one_document(client: TestClient) -> None:
    first = upload_text(client, "Vacation policy: 18 days per year.", name="first.txt").json()
    upload_text(client, "Vacation policy for contractors: 10 days.", name="second.txt")
    response = client.post(
        "/api/ask", json={"question": "vacation policy", "document_ids": [first["id"]]}
    )
    sources = response.json()["sources"]
    assert sources
    assert all(source["document_id"] == first["id"] for source in sources)


def test_deleting_a_document_then_deleting_it_again(client: TestClient) -> None:
    document_id = upload_text(client, "Some stored text about policies.").json()["id"]
    assert client.delete(f"/api/documents/{document_id}").status_code == 204
    assert client.delete(f"/api/documents/{document_id}").status_code == 404


def test_clear_all_removes_every_document(client: TestClient) -> None:
    upload_text(client, "First document text.", name="one.txt")
    upload_text(client, "Second document text.", name="two.txt")
    response = client.delete("/api/documents")
    assert response.status_code == 200
    assert response.json()["deleted_documents"] == 2
    assert client.get("/api/documents").json()["documents"] == []


def test_web_page_is_served_at_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "DocuMind" in response.text


def _claude_app(settings: Settings, error: Exception | None = None, text: str | None = None):
    """Build an app in Claude mode, but with a fake client in place of the real API."""
    claude_settings = settings.model_copy(update={"anthropic_api_key": "test-key", "demo_mode": False})
    app = create_app(claude_settings)
    messages = FakeMessages(error=error, result=text_response(text) if text else None)
    app.state.answerer = ClaudeAnswerer(FakeClient(messages), model="test-model")
    return app


def test_health_reports_claude_mode_when_key_is_set(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"anthropic_api_key": "test-key", "demo_mode": False}))
    with TestClient(app) as client:
        assert client.get("/api/health").json()["mode"] == "claude"


def test_claude_timeout_returns_504_without_leaking_the_key(settings: Settings, sample_text: str) -> None:
    app = _claude_app(settings, error=anthropic.APITimeoutError(request=REQUEST))
    client = TestClient(app)
    upload_text(client, sample_text)
    response = client.post("/api/ask", json={"question": "How many vacation days?"})
    assert response.status_code == 504
    assert "detail" in response.json()
    assert "test-key" not in response.text


def test_claude_answer_is_returned_with_sources(settings: Settings, sample_text: str) -> None:
    app = _claude_app(settings, text="Employees receive 18 paid vacation days [S1].")
    client = TestClient(app)
    upload_text(client, sample_text)
    body = client.post("/api/ask", json={"question": "How many vacation days?"}).json()
    assert body["mode"] == "claude"
    assert body["answer"] == "Employees receive 18 paid vacation days [S1]."
    assert body["insufficient_evidence"] is False
