"""Pydantic schemas: the exact shapes of data going in and out of the API.

Pydantic checks types and limits automatically. Bad input becomes a clear
422 error before our own code runs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DocumentSummary(BaseModel):
    """What the API tells the user about one stored document. The file itself is not returned."""

    id: int
    filename: str
    file_type: Literal["pdf", "txt"]
    size_bytes: int
    readable_pages: int | None
    chunk_count: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class ClearDocumentsResponse(BaseModel):
    deleted_documents: int


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    # None or an empty list means "search all documents".
    document_ids: list[int] | None = None

    @field_validator("question")
    @classmethod
    def strip_and_check_question(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Question must contain at least 3 characters.")
        return cleaned


class SourceReference(BaseModel):
    """One passage the answer is based on. The label (S1, S2, ...) matches the citations in the answer."""

    label: str
    document_id: int
    filename: str
    page_number: int | None
    chunk_index: int
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    mode: Literal["demo", "claude"]
    insufficient_evidence: bool
    sources: list[SourceReference]


class HealthResponse(BaseModel):
    status: str
    mode: Literal["demo", "claude"]
    version: str
    max_upload_mb: float
    model: str | None  # only set in Claude mode
