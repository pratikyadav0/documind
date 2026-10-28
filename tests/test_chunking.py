"""Tests for splitting text into overlapping chunks."""

import pytest

from app.chunking import chunk_pages, split_text
from app.extraction import PageText


def test_short_text_becomes_one_chunk() -> None:
    assert split_text("A short note.", chunk_size=100, chunk_overlap=10) == ["A short note."]


def test_no_chunk_is_longer_than_chunk_size() -> None:
    text = " ".join(f"word{i}" for i in range(300))
    chunks = split_text(text, chunk_size=120, chunk_overlap=30)
    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_neighbouring_chunks_share_words() -> None:
    text = " ".join(f"w{i}" for i in range(200))
    chunks = split_text(text, chunk_size=100, chunk_overlap=30)
    assert len(chunks) > 1
    for first, second in zip(chunks, chunks[1:]):
        last_word_of_first = first.split()[-1]
        assert last_word_of_first in second.split()


def test_every_word_appears_in_at_least_one_chunk() -> None:
    words = [f"term{i}" for i in range(150)]
    chunks = split_text(" ".join(words), chunk_size=90, chunk_overlap=20)
    covered = {word for chunk in chunks for word in chunk.split()}
    assert covered == set(words)


@pytest.mark.parametrize(
    "chunk_size, chunk_overlap",
    [(0, 0), (-5, 0), (10, 10), (10, 50), (10, -1)],
)
def test_invalid_chunk_settings_are_rejected(chunk_size: int, chunk_overlap: int) -> None:
    with pytest.raises(ValueError):
        split_text("some text here", chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def test_chunk_pages_keeps_page_numbers_and_never_mixes_pages() -> None:
    pages = [
        PageText(page_number=1, text="alpha beta gamma delta"),
        PageText(page_number=2, text="epsilon zeta eta theta"),
    ]
    chunks = chunk_pages(pages, chunk_size=100, chunk_overlap=10)
    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert "epsilon" not in chunks[0].text
    assert "alpha" not in chunks[1].text


def test_chunk_index_is_continuous_across_pages() -> None:
    pages = [
        PageText(page_number=1, text=" ".join(f"a{i}" for i in range(60))),
        PageText(page_number=2, text=" ".join(f"b{i}" for i in range(60))),
    ]
    chunks = chunk_pages(pages, chunk_size=80, chunk_overlap=10)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert len({chunk.page_number for chunk in chunks}) == 2
