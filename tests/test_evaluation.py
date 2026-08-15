"""Tests for the ruler itself.

A broken metric is worse than no metric: it produces a number, the number
looks plausible, and every decision downstream is made on it. These tests
pin down the two behaviours that are easy to get subtly wrong — evidence
mode, and the strict single-chunk matching rule.
"""

import csv
from pathlib import Path

import pytest

from src.evaluation import (
    EVIDENCE_MODES,
    FAILURE_LABELS,
    Evidence,
    GoldSpan,
    any_evidence_at_k,
    classify_failure,
    document_recall_at_k,
    evidence_coverage_at_k,
    first_gold_span_rank,
    gold_span_any_recall_at_k,
    gold_span_coverage_at_k,
    group_coverages,
    is_abstention,
    normalise,
    normalised_with_offsets,
    unfindable_evidence,
)
from src.generation import SYSTEM_PROMPT
from src.retrieval import RetrievedChunk

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
SPANS_CSV = Path("data/evaluation/evidence_spans.csv")

def _read_gold_rows(path: Path) -> list[dict]:
    """csv.DictReader, tolerant of a stray blank line before the header.

    evidence.csv currently carries one (documented in the Phase 5
    reproducibility gate); this must not require editing the data file to
    keep the tests passing.
    """
    lines = [line for line in path.open(encoding="utf-8") if line.strip()]
    return list(csv.DictReader(lines))



def _chunk(text: str, document: str = "a.pdf", index: int = 0) -> RetrievedChunk:
    """A retrieved chunk with only the fields the metrics actually read."""
    return RetrievedChunk(
        text=text,
        source_document=document,
        chunk_index=index,
        page_numbers=[1],
        score=0.9,
    )


def _evidence(evidence_id: str, text: str, document: str = "a.pdf") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        question_id="q000",
        relevant_document=document,
        relevant_pages="1",
        evidence_text=text,
    )


# --------------------------------------------------------------------------
# Evidence mode
# --------------------------------------------------------------------------
TWO_PASSAGES = [_evidence("e1", "revenue was 100"), _evidence("e2", "profit was 20")]


def test_all_mode_gives_partial_credit():
    """Conjunctive: one of two required facts found is genuinely half an answer."""
    retrieved = [_chunk("total revenue was 100 for the year")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5, mode="all") == 0.5


def test_any_mode_is_all_or_nothing():
    """Disjunctive: one sufficient passage IS the whole requirement met.

    Scoring 0.5 here would penalise retrieval for not also finding a second
    copy of a fact it already found — a metric bug, not a retrieval failure.
    """
    retrieved = [_chunk("total revenue was 100 for the year")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5, mode="any") == 1.0


def test_any_mode_scores_zero_when_nothing_matches():
    retrieved = [_chunk("unrelated boilerplate about the auditor")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5, mode="any") == 0.0


def test_modes_agree_when_everything_is_retrieved():
    """The modes must only differ on PARTIAL retrieval, never on full."""
    retrieved = [_chunk("revenue was 100"), _chunk("profit was 20")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5, mode="all") == 1.0
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5, mode="any") == 1.0


def test_default_mode_is_conjunctive():
    """Omitting the mode must not silently inflate scores."""
    retrieved = [_chunk("total revenue was 100 for the year")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=5) == 0.5


def test_unknown_mode_raises():
    """A typo'd mode must fail loudly, not fall back to a default."""
    with pytest.raises(ValueError):
        evidence_coverage_at_k([], TWO_PASSAGES, k=5, mode="either")


# --------------------------------------------------------------------------
# Matching rules shared by all three metrics
# --------------------------------------------------------------------------
def test_k_truncates_the_retrieved_list():
    """Recall@1 must not see the chunk that ranked 2nd."""
    retrieved = [_chunk("nothing here"), _chunk("revenue was 100")]
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=1) == 0.0
    assert evidence_coverage_at_k(retrieved, TWO_PASSAGES, k=2) == 0.5


def test_match_must_sit_inside_a_single_chunk():
    """Two chunks each holding half a snippet is NOT a match.

    The top-k chunks are not adjacent in the source, so a match spanning two
    of them would be an artefact of retrieval order — the model never saw the
    passage intact.
    """
    retrieved = [_chunk("revenue was"), _chunk("100")]
    assert any_evidence_at_k(retrieved, [_evidence("e1", "revenue was 100")], k=5) is False


def test_matching_ignores_pdf_whitespace_damage():
    """Extracted text carries stray line breaks; the snippet must still match."""
    retrieved = [_chunk("total\n  revenue   was\n100 for the year")]
    assert any_evidence_at_k(retrieved, [_evidence("e1", "revenue was 100")], k=5) is True


def test_document_recall_ignores_text():
    """The generous metric only asks whether we reached the right report."""
    retrieved = [_chunk("completely unrelated text", document="a.pdf")]
    assert document_recall_at_k(retrieved, [_evidence("e1", "x", "a.pdf")], k=5) is True
    assert document_recall_at_k(retrieved, [_evidence("e1", "x", "b.pdf")], k=5) is False


def test_unfindable_evidence_reports_snippets_no_chunk_contains():
    """A straddling snippet caps coverage forever — it must be reported, not absorbed."""
    chunks = ["revenue was 100", "profit was 20"]
    evidence = [*TWO_PASSAGES, _evidence("e3", "revenue was 100 and profit was 20")]
    assert unfindable_evidence(evidence, chunks) == ["e3"]


# --------------------------------------------------------------------------
# Abstention (Phase 6) — no API calls, this is pure string logic
# --------------------------------------------------------------------------
def test_abstention_detected():
    assert is_abstention("I don't know.") is True


def test_abstention_detection_ignores_case_and_whitespace():
    assert is_abstention("  I DON'T KNOW.  ") is True


def test_answer_that_merely_mentions_not_knowing_is_not_an_abstention():
    """The dangerous near-miss: an answer that hedges but still asserts facts.

    Scoring this as an abstention would credit the model for honesty while it
    was in fact stating an unverified number.
    """
    answer = "Revenue was 443 crore, though I don't know if that is consolidated."
    assert is_abstention(answer) is False


def test_abstention_phrase_matches_the_system_prompt():
    """The detector and the prompt that produces the phrase must not drift.

    If someone reworded SYSTEM_PROMPT to say "Not stated in the context", every
    abstention would be silently reclassified as a hallucination.
    """
    from src.evaluation import ABSTENTION_PHRASE

    assert ABSTENTION_PHRASE in SYSTEM_PROMPT.lower()


# --------------------------------------------------------------------------
# Failure taxonomy
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "evidence_retrieved, correct, abstained, expected",
    [
        (True, True, False, "grounded_correct"),
        (True, False, False, "generation_failure"),
        (True, False, True, "generation_refusal"),
        (False, True, False, "unsupported_correct"),
        (False, False, True, "retrieval_failure_honest"),
        (False, False, False, "retrieval_failure_hallucinated"),
    ],
)
def test_failure_taxonomy(evidence_retrieved, correct, abstained, expected):
    assert classify_failure(evidence_retrieved, correct, abstained) == expected


def test_every_taxonomy_label_is_documented():
    """A label with no description would print as a bare slug in the report."""
    produced = {
        classify_failure(ev, correct, abst)
        for ev in (True, False)
        for correct in (True, False)
        for abst in (True, False)
    }
    assert produced <= set(FAILURE_LABELS)


def test_correct_without_evidence_is_never_called_a_success():
    """The quadrant that makes a memorised answer look like a working system."""
    assert classify_failure(False, correct=True, abstained=False) != "grounded_correct"


# --------------------------------------------------------------------------
# Offset mapping (Phase 7A) — the bridge from normalised to raw coordinates
# --------------------------------------------------------------------------
def test_normalised_with_offsets_matches_normalise():
    """The two normalisers must never disagree, or every offset shifts."""
    text = "  The  Company\n\nhas ISSUED\tfresh equity.  "
    normalised, offsets = normalised_with_offsets(text)
    assert normalised == normalise(text)
    assert len(offsets) == len(normalised)


def test_offsets_round_trip_through_raw_text():
    """A span found in normalised space must slice the right raw substring."""
    text = "Return on Net worth\n\n 0.16   0.11  -32%\nRefer point No. (b)"
    normalised, offsets = normalised_with_offsets(text)
    needle = normalise("0.16 0.11 -32%")

    begin = normalised.index(needle)
    start, end = offsets[begin], offsets[begin + len(needle) - 1] + 1
    assert normalise(text[start:end]) == needle


def test_offsets_are_monotonic():
    """Non-decreasing offsets are what make the mapping usable at all."""
    _, offsets = normalised_with_offsets("a  b\n\nc   D e")
    assert offsets == sorted(offsets)


# --------------------------------------------------------------------------
# Gold span metrics
# --------------------------------------------------------------------------
def _span(
    evidence_id: str,
    start: int,
    end: int,
    document: str = "a.pdf",
    group_id: str = "",
) -> GoldSpan:
    return GoldSpan(
        evidence_id=evidence_id,
        question_id="q000",
        source_document=document,
        start_char=start,
        end_char=end,
        group_id=group_id,
    )


def _placed(start: int, end: int, document: str = "a.pdf") -> RetrievedChunk:
    """A retrieved chunk defined only by where it sits in the source."""
    return RetrievedChunk(
        text="", source_document=document, chunk_index=0,
        page_numbers=[1], score=0.9, start_char=start, end_char=end,
    )


def test_two_adjacent_chunks_jointly_cover_a_straddling_span():
    """THE reason spans exist. Text matching scores this 0; the model saw it all."""
    span = [_span("e1", 90, 110)]
    retrieved = [_placed(0, 100), _placed(100, 200)]
    assert gold_span_coverage_at_k(retrieved, span, k=5) == 1.0
    assert gold_span_any_recall_at_k(retrieved, span, k=5) is True


def test_partial_coverage_is_graded():
    """Half a span retrieved scores 0.5 — near-misses stay distinguishable."""
    span = [_span("e1", 0, 100)]
    assert gold_span_coverage_at_k([_placed(0, 50)], span, k=5) == 0.5


def test_partial_coverage_is_not_a_hit():
    """Graded coverage, binary recall. 0.5 covered is not 'retrieved'."""
    assert gold_span_any_recall_at_k([_placed(0, 50)], [_span("e1", 0, 100)], k=5) is False


def test_overlapping_chunks_are_not_double_counted():
    """Overlapping chunks share characters; naive summing would exceed 1.0."""
    span = [_span("e1", 0, 100)]
    retrieved = [_placed(0, 60), _placed(50, 100)]
    assert gold_span_coverage_at_k(retrieved, span, k=5) == 1.0


def test_chunks_from_another_document_never_contribute():
    """Offsets are per-document coordinates; mixing them invents coverage."""
    span = [_span("e1", 0, 100, document="a.pdf")]
    assert gold_span_coverage_at_k([_placed(0, 100, "b.pdf")], span, k=5) == 0.0


def test_span_coverage_respects_evidence_mode():
    """all -> mean of units; any -> best unit."""
    spans = [_span("e1", 0, 100), _span("e2", 200, 300)]
    retrieved = [_placed(0, 100)]          # first fully covered, second missed
    assert gold_span_coverage_at_k(retrieved, spans, k=5, mode="all") == 0.5
    assert gold_span_coverage_at_k(retrieved, spans, k=5, mode="any") == 1.0


def test_span_metrics_respect_k():
    span = [_span("e1", 200, 300)]
    retrieved = [_placed(0, 100), _placed(200, 300)]
    assert gold_span_coverage_at_k(retrieved, span, k=1) == 0.0
    assert gold_span_coverage_at_k(retrieved, span, k=2) == 1.0


def test_first_gold_span_rank_reports_any_overlap():
    """Rank measures where the retriever got warm, not where it succeeded."""
    span = [_span("e1", 100, 200)]
    retrieved = [_placed(0, 50), _placed(60, 90), _placed(190, 260)]
    assert first_gold_span_rank(retrieved, span) == 3
    assert first_gold_span_rank([_placed(0, 50)], span) is None


# --------------------------------------------------------------------------
# Evidence groups — one required fact, several valid locations
# --------------------------------------------------------------------------
# The same fact on p.43 and p.70. Retrieving EITHER answers the question.
ALTERNATIVES = [
    _span("e_p70", 1000, 1100, group_id="g1"),
    _span("e_p43", 5000, 5100, group_id="g1"),
]


def test_either_alternative_fully_satisfies_its_group():
    """The correction this whole refinement exists for."""
    assert gold_span_coverage_at_k([_placed(1000, 1100)], ALTERNATIVES, k=5) == 1.0
    assert gold_span_coverage_at_k([_placed(5000, 5100)], ALTERNATIVES, k=5) == 1.0


def test_finding_both_alternatives_is_not_worth_more_than_one():
    """A duplicate is not extra evidence; the metric must not reward it."""
    both = [_placed(1000, 1100), _placed(5000, 5100)]
    assert gold_span_coverage_at_k(both, ALTERNATIVES, k=5) == 1.0


def test_group_takes_the_best_alternative_not_the_mean():
    """Averaging alternatives would penalise not finding a duplicate."""
    retrieved = [_placed(1000, 1100), _placed(5000, 5050)]   # 100% and 50%
    assert group_coverages(retrieved, ALTERNATIVES, k=5) == {"g1": 1.0}


def test_all_groups_are_required_even_when_each_has_alternatives():
    """q010's shape: four required facts, each available in two places."""
    spans = [
        _span("a1", 0, 100, group_id="g1"), _span("a2", 900, 1000, group_id="g1"),
        _span("b1", 100, 200, group_id="g2"), _span("b2", 1000, 1100, group_id="g2"),
    ]
    # One alternative of g1 only: one fact of two.
    assert gold_span_coverage_at_k([_placed(900, 1000)], spans, k=5, mode="all") == 0.5
    # One alternative from each group: both facts covered.
    assert gold_span_coverage_at_k(
        [_placed(0, 100), _placed(1000, 1100)], spans, k=5, mode="all"
    ) == 1.0


def test_ungrouped_spans_each_form_their_own_group():
    """Backward compatibility: no group_id must behave as it did before."""
    spans = [_span("e1", 0, 100), _span("e2", 200, 300)]
    assert gold_span_coverage_at_k([_placed(0, 100)], spans, k=5, mode="all") == 0.5


def test_any_recall_needs_one_whole_fact_not_one_whole_alternative_each():
    """Half of each alternative is still zero facts retrieved."""
    retrieved = [_placed(1000, 1050), _placed(5000, 5050)]
    assert gold_span_any_recall_at_k(retrieved, ALTERNATIVES, k=5) is False


def test_stale_index_without_offsets_raises_instead_of_scoring_zero():
    """A pre-Phase-7A index must fail loudly, not look like a total regression."""
    stale = RetrievedChunk(text="", source_document="a.pdf", chunk_index=0,
                           page_numbers=[1], score=0.9)
    with pytest.raises(ValueError, match="predates Phase 7A"):
        gold_span_coverage_at_k([stale], [_span("e1", 0, 10)], k=5)


# --------------------------------------------------------------------------
# The gold set on disk
# --------------------------------------------------------------------------
def test_derived_spans_round_trip_against_the_evidence_text():
    """Every derived offset still slices out its own evidence snippet.

    This is the check that would catch a re-extracted PDF silently shifting
    every offset in the file.
    """
    from src.ingestion import load_pdf_pages, source_text

    spans = list(csv.DictReader(SPANS_CSV.open(encoding="utf-8")))
    evidence = {r["evidence_id"]: r for r in _read_gold_rows(EVIDENCE_CSV)}
    assert len(spans) == len(evidence), "a gold row has no derived span"

    cache: dict[str, str] = {}
    for row in spans:
        document = row["source_document"]
        if document not in cache:
            cache[document] = source_text(load_pdf_pages(Path("data/documents") / document))
        sliced = cache[document][int(row["start_char"]):int(row["end_char"])]
        assert normalise(sliced) == normalise(evidence[row["evidence_id"]]["evidence_text"]), (
            f"{row['evidence_id']} offsets no longer match its evidence text — "
            f"re-run scripts/derive_gold_spans.py"
        )
        assert row["group_id"] == evidence[row["evidence_id"]]["group_id"]


def test_alternatives_in_a_group_share_the_same_evidence_text():
    """Alternatives are the same FACT in two places. Different text would mean
    they are different facts and must not share a group."""
    rows = _read_gold_rows(EVIDENCE_CSV)
    by_group: dict[str, set[str]] = {}
    for row in rows:
        by_group.setdefault(row["group_id"], set()).add(normalise(row["evidence_text"]))
    for group_id, texts in by_group.items():
        if group_id == "q019_g1":
            continue   # q019's alternatives are genuinely different wordings
        assert len(texts) == 1, f"{group_id} groups rows with different text"



def test_every_question_declares_a_valid_evidence_mode():
    """A missing or misspelt mode would silently change what the metric means."""
    rows = _read_gold_rows(QUESTIONS_CSV)
    assert rows, "questions.csv is empty"
    for row in rows:
        assert row["evidence_mode"] in EVIDENCE_MODES, row["question_id"]


def test_any_mode_is_only_used_where_there_are_alternatives():
    """"any" on a single-passage question is meaningless and hides a mistake."""
    questions = _read_gold_rows(QUESTIONS_CSV)
    evidence = _read_gold_rows(EVIDENCE_CSV)

    counts: dict[str, int] = {}
    for row in evidence:
        counts[row["question_id"]] = counts.get(row["question_id"], 0) + 1

    for row in questions:
        if row["evidence_mode"] == "any":
            assert counts.get(row["question_id"], 0) > 1, (
                f"{row['question_id']} is mode=any but has one evidence row"
            )
