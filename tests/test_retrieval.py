"""Tests for keyword retrieval and ranking."""

from app.retrieval import KeywordRetriever, RetrievalCandidate, make_excerpt, tokenize


def make_candidate(chunk_id: int, text: str, chunk_index: int | None = None) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id=1,
        filename="handbook.txt",
        page_number=None,
        chunk_index=chunk_id if chunk_index is None else chunk_index,
        text=text,
    )


def test_tokenize_lowercases_and_removes_stopwords() -> None:
    assert tokenize("The Vacation policy is 18 days") == ["vacation", "policy", "18", "days"]


def test_most_relevant_chunk_ranks_first() -> None:
    candidates = [
        make_candidate(1, "Remote work is allowed two days a week."),
        make_candidate(2, "Vacation: 18 paid vacation days per year."),
        make_candidate(3, "Expense receipts are required above 25 dollars."),
    ]
    ranked = KeywordRetriever().rank("How many vacation days do I get?", candidates, top_k=3)
    assert ranked[0].candidate.chunk_id == 2
    assert 3 not in [item.candidate.chunk_id for item in ranked]


def test_no_matching_words_returns_nothing() -> None:
    candidates = [make_candidate(1, "Expense receipts are required above 25 dollars.")]
    assert KeywordRetriever().rank("quantum chromodynamics", candidates, top_k=3) == []


def test_question_made_only_of_stopwords_returns_nothing() -> None:
    candidates = [make_candidate(1, "Vacation days are 18 per year.")]
    assert KeywordRetriever().rank("what is the of", candidates, top_k=3) == []


def test_top_k_limits_the_number_of_results() -> None:
    candidates = [make_candidate(i, f"policy number {i} applies") for i in range(1, 6)]
    ranked = KeywordRetriever().rank("policy", candidates, top_k=2)
    assert len(ranked) == 2


def test_equal_scores_are_ordered_by_chunk_index() -> None:
    candidates = [
        make_candidate(10, "security policy for laptops", chunk_index=5),
        make_candidate(11, "security policy for laptops", chunk_index=2),
    ]
    ranked = KeywordRetriever().rank("security policy", candidates, top_k=2)
    assert [item.candidate.chunk_index for item in ranked] == [2, 5]


def test_no_candidates_returns_nothing() -> None:
    assert KeywordRetriever().rank("anything at all", [], top_k=3) == []


def test_make_excerpt_shortens_at_a_word_boundary() -> None:
    text = "one two three four five six seven"
    # The 15-character cut lands inside "four", so the excerpt stops after the last full word.
    assert make_excerpt(text, 15) == "one two three..."
