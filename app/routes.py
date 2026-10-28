"""HTTP routes: the layer that receives requests and calls the other modules.

Routes stay short on purpose. Validation lives in extraction.py, search in
retrieval.py, and AI calls in llm.py.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.chunking import chunk_pages
from app.config import APP_VERSION, Settings
from app.errors import AppError
from app.extraction import clean_filename, extract_text, validate_upload
from app.llm import INSUFFICIENT_EVIDENCE_MESSAGE, Answerer
from app.retrieval import KeywordRetriever, ScoredChunk, make_excerpt
from app.schemas import (
    AskRequest,
    AskResponse,
    ClearDocumentsResponse,
    DocumentListResponse,
    DocumentSummary,
    HealthResponse,
    SourceReference,
)
from app.storage import DocumentStore

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api")
EXCERPT_LENGTH = 240


# Dependencies: FastAPI calls these to get the objects that were stored on app.state at startup.
def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> DocumentStore:
    return request.app.state.store


def get_answerer(request: Request) -> Answerer:
    return request.app.state.answerer


def get_retriever(request: Request) -> KeywordRetriever:
    return request.app.state.retriever


@api_router.get("/health", response_model=HealthResponse)
def health_check(
    answerer: Answerer = Depends(get_answerer),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Confirms the server is running. Also tells the browser the mode and the upload limit it must follow."""
    # The model name is public configuration, not a secret. The API key is never included.
    model_name = settings.anthropic_model if answerer.mode == "claude" else None
    return HealthResponse(
        status="ok",
        mode=answerer.mode,
        version=APP_VERSION,
        max_upload_mb=settings.max_upload_mb,
        model=model_name,
    )


@api_router.post("/documents", status_code=201, response_model=DocumentSummary)
async def upload_document(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
) -> DocumentSummary:
    """Validate an uploaded PDF or TXT file, extract its text, and store the chunks."""
    filename = clean_filename(file.filename or "")

    # Read one byte more than the limit. If that extra byte arrives, the file is too big.
    data = await file.read(settings.max_upload_bytes + 1)
    file_type = validate_upload(filename, data, settings.max_upload_bytes)

    # A fingerprint (SHA-256) lets us spot the same file uploaded twice without storing the file.
    content_hash = hashlib.sha256(data).hexdigest()
    existing_id = store.find_document_id_by_hash(content_hash)
    if existing_id is not None:
        raise AppError(409, f"This file is already stored as document {existing_id}.")

    # PDF parsing is CPU work, so run it in a worker thread to keep the server responsive.
    pages = await run_in_threadpool(extract_text, file_type, data)
    chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
    readable_pages = len(pages) if file_type == "pdf" else None

    # The uploaded bytes are not stored. Only the extracted text chunks are kept.
    summary = store.save_document(
        filename=filename,
        file_type=file_type,
        size_bytes=len(data),
        content_hash=content_hash,
        readable_pages=readable_pages,
        chunks=chunks,
    )
    logger.info("Stored document id=%s type=%s chunks=%s", summary.id, file_type, summary.chunk_count)
    return summary


@api_router.get("/documents", response_model=DocumentListResponse)
def list_documents(store: DocumentStore = Depends(get_store)) -> DocumentListResponse:
    return DocumentListResponse(documents=store.list_documents())


@api_router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, store: DocumentStore = Depends(get_store)) -> Response:
    if not store.delete_document(document_id):
        raise AppError(404, f"Document {document_id} was not found.")
    return Response(status_code=204)


@api_router.delete("/documents", response_model=ClearDocumentsResponse)
def clear_documents(store: DocumentStore = Depends(get_store)) -> ClearDocumentsResponse:
    """Delete all stored documents and their text chunks."""
    return ClearDocumentsResponse(deleted_documents=store.clear_all())


@api_router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    settings: Settings = Depends(get_settings),
    store: DocumentStore = Depends(get_store),
    retriever: KeywordRetriever = Depends(get_retriever),
    answerer: Answerer = Depends(get_answerer),
) -> AskResponse:
    """Find the relevant passages, then ask the answerer (Claude or demo) to answer from them."""
    if store.count_documents() == 0:
        raise AppError(404, "No documents uploaded yet. Upload a PDF or TXT file first.")

    requested_ids = payload.document_ids or []
    if requested_ids:
        found_ids = store.existing_document_ids(requested_ids)
        missing_ids = sorted(set(requested_ids) - found_ids)
        if missing_ids:
            raise AppError(404, f"Document(s) not found: {missing_ids}.")

    candidates = store.load_candidates(requested_ids)
    ranked = retriever.rank(payload.question, candidates, settings.top_k)

    # No keyword matches means no evidence. We say so directly and do not call the AI at all.
    if not ranked:
        return AskResponse(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            mode=answerer.mode,
            insufficient_evidence=True,
            sources=[],
        )

    answer_text = await run_in_threadpool(answerer.answer, payload.question, ranked)
    sources = [
        _build_source(label=f"S{position}", item=item)
        for position, item in enumerate(ranked, start=1)
    ]
    return AskResponse(
        answer=answer_text,
        mode=answerer.mode,
        insufficient_evidence=INSUFFICIENT_EVIDENCE_MESSAGE in answer_text,
        sources=sources,
    )


def _build_source(label: str, item: ScoredChunk) -> SourceReference:
    candidate = item.candidate
    return SourceReference(
        label=label,
        document_id=candidate.document_id,
        filename=candidate.filename,
        page_number=candidate.page_number,
        chunk_index=candidate.chunk_index,
        excerpt=make_excerpt(candidate.text, EXCERPT_LENGTH),
    )
