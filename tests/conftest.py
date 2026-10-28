"""Shared pytest fixtures.

Each test gets its own temporary database and its own settings. The tests never
read the real data folder, never read a real .env file, and never need an API key.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application import create_app
from app.config import Settings

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "synthetic_company_handbook.txt"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        anthropic_api_key="",
        demo_mode=True,
        database_path=tmp_path / "test.db",
        chunk_size=200,
        chunk_overlap=40,
        top_k=3,
        max_upload_mb=0.01,  # about 10 KB, so size-limit tests stay fast
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def sample_text() -> str:
    return SAMPLE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def make_pdf() -> Callable[[list[str]], bytes]:
    """Return a function that builds a small, valid PDF with one line of text per page.

    We write the PDF bytes ourselves, so the tests need no extra PDF-writing library.
    """

    def build(page_texts: list[str]) -> bytes:
        objects: dict[int, bytes] = {
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        }
        page_ids: list[int] = []
        next_id = 4
        for text in page_texts:
            page_id, content_id = next_id, next_id + 1
            next_id += 2
            page_ids.append(page_id)
            stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
            objects[content_id] = (
                b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
            )
            objects[page_id] = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 800] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()

        output = bytearray(b"%PDF-1.4\n")
        offsets: dict[int, int] = {}
        for object_id in sorted(objects):
            offsets[object_id] = len(output)
            output += b"%d 0 obj\n" % object_id + objects[object_id] + b"\nendobj\n"

        xref_position = len(output)
        count = max(objects) + 1
        output += b"xref\n0 %d\n" % count
        output += b"0000000000 65535 f \n"
        for object_id in range(1, count):
            output += b"%010d 00000 n \n" % offsets[object_id]
        output += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            count,
            xref_position,
        )
        return bytes(output)

    return build
