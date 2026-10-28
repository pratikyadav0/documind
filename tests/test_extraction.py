"""Tests for file validation and text extraction."""

import io
from collections.abc import Callable

import pypdf
import pytest

from app.errors import DocumentValidationError
from app.extraction import extract_text, validate_upload

MAX_BYTES = 1024


def test_accepts_plain_text_file() -> None:
    assert validate_upload("notes.txt", b"Hello world", MAX_BYTES) == "txt"


def test_extension_check_ignores_upper_case() -> None:
    assert validate_upload("NOTES.TXT", b"Hello world", MAX_BYTES) == "txt"


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(DocumentValidationError) as info:
        validate_upload("photo.png", b"not really a picture", MAX_BYTES)
    assert info.value.status_code == 415


def test_rejects_empty_file() -> None:
    with pytest.raises(DocumentValidationError) as info:
        validate_upload("empty.txt", b"", MAX_BYTES)
    assert info.value.status_code == 400


def test_rejects_file_over_size_limit() -> None:
    with pytest.raises(DocumentValidationError) as info:
        validate_upload("big.txt", b"a" * (MAX_BYTES + 1), MAX_BYTES)
    assert info.value.status_code == 413


def test_rejects_pdf_extension_without_pdf_content() -> None:
    with pytest.raises(DocumentValidationError) as info:
        validate_upload("fake.pdf", b"plain text pretending to be a PDF", MAX_BYTES)
    assert info.value.status_code == 415


def test_rejects_text_file_containing_binary_bytes() -> None:
    with pytest.raises(DocumentValidationError) as info:
        validate_upload("data.txt", b"abc\x00def", MAX_BYTES)
    assert info.value.status_code == 415


def test_txt_extraction_returns_one_page_without_page_number() -> None:
    pages = extract_text("txt", b"  Line one.\nLine two.  ")
    assert len(pages) == 1
    assert pages[0].page_number is None
    assert pages[0].text == "Line one.\nLine two."


def test_non_utf8_text_is_rejected() -> None:
    with pytest.raises(DocumentValidationError) as info:
        extract_text("txt", b"\xff\xfe broken bytes")
    assert info.value.status_code == 415


def test_whitespace_only_text_is_rejected_as_empty() -> None:
    with pytest.raises(DocumentValidationError) as info:
        extract_text("txt", b"   \n\t  ")
    assert info.value.status_code == 422


def test_pdf_text_is_extracted_with_page_numbers(make_pdf: Callable[[list[str]], bytes]) -> None:
    data = make_pdf(["Page one has the vacation policy.", "Page two has the remote policy."])
    pages = extract_text("pdf", data)
    assert [page.page_number for page in pages] == [1, 2]
    assert "vacation policy" in pages[0].text
    assert "remote policy" in pages[1].text


def test_pdf_without_any_text_is_rejected() -> None:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    with pytest.raises(DocumentValidationError) as info:
        extract_text("pdf", buffer.getvalue())
    assert info.value.status_code == 422


def test_damaged_pdf_is_rejected_safely() -> None:
    with pytest.raises(DocumentValidationError) as info:
        extract_text("pdf", b"%PDF-1.4 this is not a real document")
    assert info.value.status_code == 422
