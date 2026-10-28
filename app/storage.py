"""Storage: saves document details and text chunks in a local SQLite file.

What is stored:
- document rows: file name, type, size, number of readable pages, upload time
- chunk rows: the extracted text pieces and their page numbers

What is NOT stored: the original uploaded file bytes. They are discarded after
text extraction. README.md explains this in more detail.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.chunking import TextChunk
from app.retrieval import RetrievalCandidate
from app.schemas import DocumentSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    content_sha256 TEXT,
    readable_pages INTEGER,
    uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL
);
"""


class DocumentStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        """Create the folder and tables if they do not exist yet.

        Databases created by an older version of DocuMind lack the content_sha256 column,
        so we add it when it is missing. This keeps existing data usable after an update.
        """
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            existing_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(documents)").fetchall()
            }
            if "content_sha256" not in existing_columns:
                connection.execute("ALTER TABLE documents ADD COLUMN content_sha256 TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(content_sha256)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection, commit on success, roll back on error, and always close."""
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        # SQLite ignores foreign keys unless this is switched on for each connection.
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def find_document_id_by_hash(self, content_hash: str) -> int | None:
        """Return the id of a stored document with the same SHA-256 fingerprint, if one exists."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE content_sha256 = ? ORDER BY id LIMIT 1",
                (content_hash,),
            ).fetchone()
        return int(row["id"]) if row else None

    def save_document(
        self,
        filename: str,
        file_type: str,
        size_bytes: int,
        content_hash: str,
        readable_pages: int | None,
        chunks: list[TextChunk],
    ) -> DocumentSummary:
        uploaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO documents "
                "(filename, file_type, size_bytes, content_sha256, readable_pages, uploaded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (filename, file_type, size_bytes, content_hash, readable_pages, uploaded_at),
            )
            document_id = int(cursor.lastrowid or 0)
            connection.executemany(
                "INSERT INTO chunks (document_id, page_number, chunk_index, text) VALUES (?, ?, ?, ?)",
                [(document_id, chunk.page_number, chunk.chunk_index, chunk.text) for chunk in chunks],
            )
        return DocumentSummary(
            id=document_id,
            filename=filename,
            file_type=file_type,  # type: ignore[arg-type]  # validated earlier as "pdf" or "txt"
            size_bytes=size_bytes,
            readable_pages=readable_pages,
            chunk_count=len(chunks),
            uploaded_at=uploaded_at,
        )

    def list_documents(self) -> list[DocumentSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT d.id, d.filename, d.file_type, d.size_bytes, d.readable_pages, "
                "d.uploaded_at, COUNT(c.id) AS chunk_count "
                "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
                "GROUP BY d.id ORDER BY d.id"
            ).fetchall()
        return [
            DocumentSummary(
                id=row["id"],
                filename=row["filename"],
                file_type=row["file_type"],
                size_bytes=row["size_bytes"],
                readable_pages=row["readable_pages"],
                chunk_count=row["chunk_count"],
                uploaded_at=row["uploaded_at"],
            )
            for row in rows
        ]

    def count_documents(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM documents").fetchone()
        return int(row["total"])

    def existing_document_ids(self, document_ids: list[int]) -> set[int]:
        if not document_ids:
            return set()
        placeholders = ", ".join("?" for _ in document_ids)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT id FROM documents WHERE id IN ({placeholders})", document_ids
            ).fetchall()
        return {int(row["id"]) for row in rows}

    def load_candidates(self, document_ids: list[int]) -> list[RetrievalCandidate]:
        """Load chunks for the given documents, or for all documents when the list is empty."""
        query = (
            "SELECT c.id AS chunk_id, c.document_id, d.filename, c.page_number, c.chunk_index, c.text "
            "FROM chunks c JOIN documents d ON d.id = c.document_id "
        )
        parameters: list[int] = []
        if document_ids:
            placeholders = ", ".join("?" for _ in document_ids)
            query += f"WHERE c.document_id IN ({placeholders}) "
            parameters = list(document_ids)
        query += "ORDER BY c.document_id, c.chunk_index"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            RetrievalCandidate(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                filename=row["filename"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                text=row["text"],
            )
            for row in rows
        ]

    def delete_document(self, document_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            deleted = cursor.rowcount > 0
        if deleted:
            self._vacuum()
        return deleted

    def clear_all(self) -> int:
        """Delete every stored document and chunk. Returns how many documents were removed."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM documents")
            deleted_count = cursor.rowcount
        self._vacuum()
        return deleted_count

    def _vacuum(self) -> None:
        # Deleted rows can stay in the database file until VACUUM rewrites it.
        # VACUUM cannot run inside a transaction, so it gets its own connection.
        connection = sqlite3.connect(self._database_path)
        try:
            connection.execute("VACUUM")
        finally:
            connection.close()
