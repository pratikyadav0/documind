"""Retrieval: find the chunks most relevant to a question.

This is KEYWORD retrieval (also called lexical or bag-of-words search).
It does NOT use embeddings or semantic search. It counts shared words, gives
rare words more weight, and sorts chunks by score.

Why start here? It has no extra cost, needs no model download, and is easy to
explain in an interview. To add embeddings later, write a new class with the
same `rank` method. The routes only depend on the Retriever protocol below.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

# Very common words that carry no meaning for search ("the", "is", "what", ...).
STOPWORDS = frozenset(
    {
        "a", "about", "all", "also", "an", "and", "any", "are", "as", "at", "be", "been",
        "by", "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
        "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "no", "not", "of",
        "on", "or", "our", "should", "so", "than", "that", "the", "their", "then", "there",
        "they", "this", "to", "was", "we", "what", "when", "where", "which", "who", "why",
        "will", "with", "would", "you", "your",
    }
)
_WORD_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievalCandidate:
    """One stored chunk that could answer the question."""

    chunk_id: int
    document_id: int
    filename: str
    page_number: int | None
    chunk_index: int
    text: str


@dataclass(frozen=True)
class ScoredChunk:
    candidate: RetrievalCandidate
    score: float


class Retriever(Protocol):
    """Any ranking method with this shape can be plugged in, including a future embedding-based one."""

    def rank(
        self, question: str, candidates: Sequence[RetrievalCandidate], top_k: int
    ) -> list[ScoredChunk]: ...


def tokenize(text: str) -> list[str]:
    """Lowercase the text, split it into words, and drop stopwords and one-letter words."""
    words = _WORD_PATTERN.findall(text.lower())
    return [word for word in words if len(word) > 1 and word not in STOPWORDS]


def make_excerpt(text: str, limit: int) -> str:
    """Shorten text for display, cutting at a word boundary when possible."""
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0]
    return shortened + "..."


class KeywordRetriever:
    """Ranks chunks by shared keywords. Rare words count more than common ones."""

    def rank(
        self, question: str, candidates: Sequence[RetrievalCandidate], top_k: int
    ) -> list[ScoredChunk]:
        query_terms = set(tokenize(question))
        if not query_terms or not candidates or top_k <= 0:
            return []

        token_counts = [Counter(tokenize(candidate.text)) for candidate in candidates]

        # Document frequency: how many chunks contain each query word.
        chunks_with_term: Counter[str] = Counter()
        for counts in token_counts:
            for term in query_terms:
                if term in counts:
                    chunks_with_term[term] += 1

        total_chunks = len(candidates)
        scored: list[ScoredChunk] = []
        for candidate, counts in zip(candidates, token_counts):
            score = _score_chunk(query_terms, counts, chunks_with_term, total_chunks)
            if score > 0:
                scored.append(ScoredChunk(candidate=candidate, score=score))

        # Sort by score (highest first). Ties go to the earlier document and chunk, so results are repeatable.
        scored.sort(
            key=lambda item: (-item.score, item.candidate.document_id, item.candidate.chunk_index)
        )
        return scored[:top_k]


def _score_chunk(
    query_terms: set[str],
    counts: Counter[str],
    chunks_with_term: Counter[str],
    total_chunks: int,
) -> float:
    total_words = sum(counts.values())
    if total_words == 0:
        return 0.0

    score = 0.0
    for term in query_terms:
        term_count = counts.get(term, 0)
        if term_count == 0:
            continue
        # Rare words are worth more. The value is larger when fewer chunks contain the term.
        inverse_frequency = math.log(1 + total_chunks / chunks_with_term[term])
        # Repeats help, but with diminishing returns: 1 + log(count).
        term_weight = 1 + math.log(term_count)
        score += term_weight * inverse_frequency

    # Divide by the square root of the length, so a long chunk does not win just for being long.
    return score / math.sqrt(total_words)
