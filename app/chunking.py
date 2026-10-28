"""Chunking: split extracted text into overlapping pieces called chunks.

Why chunk?
- Search works better on short passages than on a whole 100-page PDF.
- Each chunk is small enough to send to the AI model along with the question.
- Overlap means a sentence cut at a boundary still appears whole in one chunk.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.extraction import PageText


@dataclass(frozen=True)
class TextChunk:
    page_number: int | None
    chunk_index: int
    text: str


def validate_chunk_settings(chunk_size: int, chunk_overlap: int) -> None:
    """Raise ValueError if the chunk settings cannot work."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split one piece of text into chunks of at most chunk_size characters."""
    validate_chunk_settings(chunk_size, chunk_overlap)

    # Trade-off: collapsing all whitespace keeps the code simple, but paragraph
    # breaks are lost. That is acceptable for keyword search.
    cleaned = " ".join(text.split())

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        if end < len(cleaned):
            # Prefer ending on a space so that words are not cut in half.
            # We only accept a space in the second half of the window, so chunks don't get tiny.
            space_position = cleaned.rfind(" ", start, end)
            if space_position > start + chunk_size // 2:
                end = space_position

        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(cleaned):
            break

        # Step back by the overlap so the next chunk repeats the end of this one.
        next_start = end - chunk_overlap
        word_start = cleaned.find(" ", next_start, end)
        if word_start != -1:
            next_start = word_start + 1
        # Always move forward, so the loop can never get stuck.
        start = max(next_start, start + 1)
    return chunks


def chunk_pages(pages: Iterable[PageText], chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    """Chunk each page separately so every chunk keeps its page number.

    Chunks never span two pages. That keeps page citations accurate.
    """
    chunks: list[TextChunk] = []
    for page in pages:
        for piece in split_text(page.text, chunk_size, chunk_overlap):
            chunks.append(
                TextChunk(page_number=page.page_number, chunk_index=len(chunks), text=piece)
            )
    return chunks
