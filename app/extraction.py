"""Document validation and text extraction.

Two steps happen here, cheapest first:
1. Validation: check the extension, size, empty file, and file signature
   BEFORE doing any real parsing.
2. Extraction: decode a .txt file, or read each page of a .pdf file.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.errors import DocumentValidationError

logger = logging.getLogger(__name__)

# Maps the allowed extension to the file type we store.
ALLOWED_EXTENSIONS = {".pdf": "pdf", ".txt": "txt"}
# Every real PDF file starts with these bytes. Checking them catches renamed files.
PDF_SIGNATURE = b"%PDF-"


@dataclass(frozen=True)
class PageText:
    """The text of one page. A .txt file has no pages, so its page_number is None."""

    page_number: int | None
    text: str


MAX_FILENAME_LENGTH = 255


def clean_filename(raw_name: str) -> str:
    """Return a safe display name. The name is only ever stored as text, never used as a file path.

    Browsers can send folder parts such as "..\\..\\secret.txt". We keep only the last part
    and drop control characters, so the stored name cannot look like a path.
    """
    # Treat both slash styles as separators, because Windows browsers send backslashes.
    last_part = raw_name.replace("\\", "/").split("/")[-1]
    printable = "".join(character for character in last_part if character.isprintable())
    cleaned = printable.strip()
    return cleaned[:MAX_FILENAME_LENGTH]


def validate_upload(filename: str, data: bytes, max_bytes: int) -> str:
    """Check an uploaded file and return its type: "pdf" or "txt".

    Raises DocumentValidationError with a status code and a message the user can read.
    """
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        shown = extension or "(none)"
        raise DocumentValidationError(415, f"Unsupported file type {shown}. Upload a .pdf or .txt file.")

    if len(data) == 0:
        raise DocumentValidationError(400, "The uploaded file is empty.")

    if len(data) > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise DocumentValidationError(413, f"The file is larger than the {max_mb:.2f} MB limit.")

    file_type = ALLOWED_EXTENSIONS[extension]
    if file_type == "pdf" and not data.startswith(PDF_SIGNATURE):
        raise DocumentValidationError(415, "The file name ends in .pdf, but the content is not a PDF.")
    if file_type == "txt" and b"\x00" in data:
        # A NUL byte almost never appears in real text, so it usually means a binary file.
        raise DocumentValidationError(415, "The .txt file appears to contain binary data.")
    return file_type


def extract_text(file_type: str, data: bytes) -> list[PageText]:
    """Return the readable pages of a document. Raises DocumentValidationError if there is no text."""
    if file_type == "txt":
        pages = _extract_txt(data)
    else:
        pages = _extract_pdf(data)

    readable_pages = [page for page in pages if page.text]
    if not readable_pages:
        raise DocumentValidationError(
            422,
            "No readable text was found in this document. Scanned PDFs need OCR, which DocuMind does not do.",
        )
    return readable_pages


def _extract_txt(data: bytes) -> list[PageText]:
    try:
        # utf-8-sig also removes a Byte Order Mark (BOM) that some Windows editors add.
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentValidationError(415, "The .txt file must be UTF-8 encoded.") from error
    return [PageText(page_number=None, text=text.strip())]


def _extract_pdf(data: bytes) -> list[PageText]:
    try:
        reader = PdfReader(io.BytesIO(data))
        # Password-protected PDFs: we try the empty password, which many "protected" files use.
        if reader.is_encrypted and not reader.decrypt(""):
            raise DocumentValidationError(422, "Password-protected PDFs are not supported.")

        pages: list[PageText] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append(PageText(page_number=page_number, text=text))
        return pages
    except (PdfReadError, ValueError) as error:
        # pypdf raises these for damaged files. We log the details and show a safe message.
        logger.info("PDF could not be parsed: %s", error)
        raise DocumentValidationError(422, "The PDF could not be read. It may be damaged.") from error
