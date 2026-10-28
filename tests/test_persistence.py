"""Tests for the SQLite database: restarts, deletion, duplicates, and old database files."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from app.application import create_app
from app.config import Settings
from app.storage import DocumentStore
from tests.test_api import upload_text


def count_rows(database_path: Path, table: str) -> int:
    connection = sqlite3.connect(database_path)
    try:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        connection.close()


def test_documents_survive_an_application_restart(settings: Settings) -> None:
    first_run = TestClient(create_app(settings))
    upload_text(first_run, "Vacation: 18 days per year.", name="policy.txt")

    # A brand-new app object on the same database file simulates restarting the server.
    second_run = TestClient(create_app(settings))
    documents = second_run.get("/api/documents").json()["documents"]
    assert [doc["filename"] for doc in documents] == ["policy.txt"]

    answer = second_run.post("/api/ask", json={"question": "vacation days"}).json()
    assert answer["sources"][0]["filename"] == "policy.txt"


def test_deleting_a_document_removes_its_stored_text(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    document_id = upload_text(client, "Secret project codename Bluebird for testing.").json()["id"]
    assert count_rows(settings.database_path, "chunks") >= 1

    assert client.delete(f"/api/documents/{document_id}").status_code == 204

    # The text must be gone from the database file, not only hidden in the list view.
    assert count_rows(settings.database_path, "documents") == 0
    assert count_rows(settings.database_path, "chunks") == 0


def test_clear_all_removes_every_chunk(settings: Settings) -> None:
    client = TestClient(create_app(settings))
    upload_text(client, "First document text.", name="one.txt")
    upload_text(client, "Second document text.", name="two.txt")
    client.delete("/api/documents")
    assert count_rows(settings.database_path, "documents") == 0
    assert count_rows(settings.database_path, "chunks") == 0


def test_same_file_uploaded_twice_is_rejected_with_409(client: TestClient) -> None:
    first = upload_text(client, "Identical content for the duplicate test.", name="a.txt")
    second = upload_text(client, "Identical content for the duplicate test.", name="b.txt")
    assert first.status_code == 201
    assert second.status_code == 409
    assert str(first.json()["id"]) in second.json()["detail"]
    assert len(client.get("/api/documents").json()["documents"]) == 1


def test_old_database_without_hash_column_is_upgraded(tmp_path: Path) -> None:
    database_path = tmp_path / "old.db"
    # Build a database with the first version's table layout (no content_sha256 column).
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            readable_pages INTEGER,
            uploaded_at TEXT NOT NULL
        );
        INSERT INTO documents (filename, file_type, size_bytes, readable_pages, uploaded_at)
        VALUES ('old.txt', 'txt', 10, NULL, '2026-01-01T00:00:00+00:00');
        """
    )
    connection.commit()
    connection.close()

    store = DocumentStore(database_path)
    store.initialize()  # must add the missing column without losing the old row

    assert store.count_documents() == 1
    assert store.find_document_id_by_hash("not-a-real-hash") is None


def test_repeated_startup_is_safe(settings: Settings) -> None:
    store = DocumentStore(settings.database_path)
    store.initialize()
    store.initialize()  # running setup twice must not fail or duplicate tables
    assert store.count_documents() == 0


def test_pdf_upload_keeps_page_numbers_for_sources(
    client: TestClient, make_pdf: Callable[[list[str]], bytes]
) -> None:
    pdf_bytes = make_pdf(["Quarterly revenue grew by twelve percent.", "Office hours are nine to five."])
    response = client.post("/api/documents", files={"file": ("report.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 201
    assert response.json()["readable_pages"] == 2

    answer = client.post("/api/ask", json={"question": "How much did quarterly revenue grow?"}).json()
    assert answer["sources"][0]["page_number"] == 1
    assert answer["sources"][0]["filename"] == "report.pdf"


def test_damaged_pdf_upload_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("broken.pdf", b"%PDF-1.4 truncated nonsense", "application/pdf")},
    )
    assert response.status_code == 422
    assert "detail" in response.json()
