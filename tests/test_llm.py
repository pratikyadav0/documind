"""Tests for the LLM layer. Every Claude call is faked, so these tests cost nothing and need no key."""

from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.config import Settings
from app.errors import LLMConfigurationError, LLMError
from app.llm import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    SYSTEM_PROMPT,
    ClaudeAnswerer,
    DemoAnswerer,
    build_claude_client,
    build_user_message,
    extract_answer_text,
)
from app.retrieval import RetrievalCandidate, ScoredChunk
from tests.fakes import FakeClient, FakeMessages, text_response

REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def make_scored(text: str = "Vacation: 18 days per year.", page: int | None = None) -> ScoredChunk:
    candidate = RetrievalCandidate(
        chunk_id=1,
        document_id=1,
        filename="handbook.txt",
        page_number=page,
        chunk_index=0,
        text=text,
    )
    return ScoredChunk(candidate=candidate, score=1.0)


def test_claude_answer_is_returned_and_request_is_grounded() -> None:
    messages = FakeMessages(result=text_response("Employees get 18 days [S1]."))
    answerer = ClaudeAnswerer(FakeClient(messages), model="test-model")

    answer = answerer.answer("How many vacation days?", [make_scored()])

    assert answer == "Employees get 18 days [S1]."
    call = messages.calls[0]
    assert call["model"] == "test-model"
    assert call["system"] == SYSTEM_PROMPT
    user_text = call["messages"][0]["content"]
    assert "[S1]" in user_text
    assert "How many vacation days?" in user_text


def test_system_prompt_covers_the_safety_rules() -> None:
    lowered = SYSTEM_PROMPT.lower()
    assert "untrusted" in lowered
    assert "ignore" in lowered or "never follow" in lowered
    assert INSUFFICIENT_EVIDENCE_MESSAGE in SYSTEM_PROMPT


def test_user_message_shows_page_numbers_when_known() -> None:
    message = build_user_message("question?", [make_scored(page=3)])
    assert "page=3" in message
    assert "<question>" in message


@pytest.mark.parametrize(
    "error, expected_status",
    [
        (anthropic.APITimeoutError(request=REQUEST), 504),
        (
            anthropic.RateLimitError("slow down", response=httpx.Response(429, request=REQUEST), body=None),
            429,
        ),
        (anthropic.APIConnectionError(request=REQUEST), 502),
        (
            anthropic.APIStatusError("boom", response=httpx.Response(500, request=REQUEST), body=None),
            502,
        ),
    ],
)
def test_api_errors_become_safe_errors_with_matching_status(
    error: Exception, expected_status: int
) -> None:
    answerer = ClaudeAnswerer(FakeClient(FakeMessages(error=error)), model="test-model")

    with pytest.raises(LLMError) as info:
        answerer.answer("a real question", [make_scored()])

    assert info.value.status_code == expected_status
    assert "boom" not in info.value.message  # raw error text is never shown to the user


def test_empty_response_is_rejected_as_malformed() -> None:
    answerer = ClaudeAnswerer(FakeClient(FakeMessages(result=SimpleNamespace(content=[]))), model="m")
    with pytest.raises(LLMError) as info:
        answerer.answer("a real question", [make_scored()])
    assert info.value.status_code == 502


def test_response_without_a_text_block_is_rejected() -> None:
    response = SimpleNamespace(content=[SimpleNamespace(type="tool_use")])
    with pytest.raises(LLMError) as info:
        extract_answer_text(response)
    assert info.value.status_code == 502


def test_text_blocks_are_joined_into_one_answer() -> None:
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="First part."),
            SimpleNamespace(type="text", text="Second part."),
        ]
    )
    assert extract_answer_text(response) == "First part.\nSecond part."


def test_missing_api_key_is_a_configuration_error() -> None:
    with pytest.raises(LLMConfigurationError) as info:
        build_claude_client(Settings(anthropic_api_key=""))
    assert info.value.status_code == 503
    assert "ANTHROPIC_API_KEY" in info.value.message


def test_client_is_created_when_a_key_is_present() -> None:
    client = build_claude_client(Settings(anthropic_api_key="test-key-not-real"))
    assert isinstance(client, anthropic.Anthropic)


def test_demo_answer_is_labeled_and_repeatable() -> None:
    answerer = DemoAnswerer()
    chunks = [make_scored(page=2)]
    first = answerer.answer("vacation?", chunks)
    second = answerer.answer("vacation?", chunks)
    assert first == second
    assert "DEMO MODE" in first
    assert "[S1]" in first
    assert answerer.mode == "demo"


def test_demo_answer_is_one_sentence_that_matches_the_question() -> None:
    from app.llm import best_sentence

    text = (
        "SYNTHETIC SAMPLE DOCUMENT for testing. "
        "Full-time employees receive 18 paid vacation days per calendar year. "
        "Expense receipts are required above 25 dollars."
    )
    sentence = best_sentence("How many vacation days do employees get?", text)
    assert sentence == "Full-time employees receive 18 paid vacation days per calendar year."


def test_demo_answer_text_contains_the_single_best_sentence() -> None:
    chunk = ScoredChunk(
        candidate=RetrievalCandidate(
            chunk_id=1, document_id=1, filename="handbook.txt", page_number=None, chunk_index=0,
            text="Header line. Full-time employees receive 18 paid vacation days. Remote work is allowed.",
        ),
        score=1.0,
    )
    answer = DemoAnswerer().answer("How many vacation days?", [chunk])
    assert answer == "DEMO MODE (no AI call): Full-time employees receive 18 paid vacation days. [S1]"
