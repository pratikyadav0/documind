"""Tests for the specific Claude API error messages, using mocked errors.

Each test simulates one failure the real SDK would raise. No network call is made.
"""

import anthropic
import httpx
import pytest

from app.errors import LLMError
from app.llm import ClaudeAnswerer
from app.retrieval import RetrievalCandidate, ScoredChunk
from tests.fakes import FakeClient, FakeMessages

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def make_chunk() -> ScoredChunk:
    candidate = RetrievalCandidate(
        chunk_id=1, document_id=1, filename="handbook.txt", page_number=None, chunk_index=0,
        text="Vacation: 18 days per year.",
    )
    return ScoredChunk(candidate=candidate, score=1.0)


def status_error(error_class: type[anthropic.APIStatusError], code: int):
    return error_class("upstream said something private", response=httpx.Response(code, request=REQUEST), body=None)


@pytest.mark.parametrize(
    "error, expected_status, expected_hint",
    [
        (status_error(anthropic.AuthenticationError, 401), 502, "ANTHROPIC_API_KEY"),
        (status_error(anthropic.PermissionDeniedError, 403), 502, "denied access"),
        (status_error(anthropic.NotFoundError, 404), 502, "ANTHROPIC_MODEL"),
        (status_error(anthropic.BadRequestError, 400), 502, "valid model ID"),
    ],
)
def test_specific_api_errors_give_a_setting_to_check(
    error: Exception, expected_status: int, expected_hint: str
) -> None:
    answerer = ClaudeAnswerer(FakeClient(FakeMessages(error=error)), model="test-model")
    with pytest.raises(LLMError) as info:
        answerer.answer("What is the vacation policy?", [make_chunk()])
    assert info.value.status_code == expected_status
    assert expected_hint in info.value.message
    # The upstream error text may contain private details, so it must never reach the user.
    assert "upstream said something private" not in info.value.message


def test_unknown_status_code_falls_back_to_a_generic_message() -> None:
    error = status_error(anthropic.InternalServerError, 500)
    answerer = ClaudeAnswerer(FakeClient(FakeMessages(error=error)), model="test-model")
    with pytest.raises(LLMError) as info:
        answerer.answer("What is the vacation policy?", [make_chunk()])
    assert info.value.status_code == 502
    assert info.value.message == "The AI service returned an error."


def test_claude_insufficient_evidence_answer_is_flagged_by_the_api(settings) -> None:
    from fastapi.testclient import TestClient

    from app.application import create_app
    from app.llm import INSUFFICIENT_EVIDENCE_MESSAGE
    from tests.fakes import text_response

    claude_settings = settings.model_copy(update={"anthropic_api_key": "test-key", "demo_mode": False})
    app = create_app(claude_settings)
    messages = FakeMessages(result=text_response(INSUFFICIENT_EVIDENCE_MESSAGE + " Nothing about Mongolia."))
    app.state.answerer = ClaudeAnswerer(FakeClient(messages), model="test-model")
    client = TestClient(app)
    client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"Vacation: 18 days per year.", "text/plain")},
    )
    body = client.post("/api/ask", json={"question": "What is the capital of Mongolia?"}).json()
    assert body["mode"] == "claude"
    assert body["insufficient_evidence"] is True
