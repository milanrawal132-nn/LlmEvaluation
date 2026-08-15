"""Tests for Phase 8's failure-analysis logic. No API key, no index, no CSVs."""

from src.evaluation import FAILURE_LABELS
import scripts.analyze_failures as lib


def _row(label, question_id="q1"):
    return {"failure_label": label, "question_id": question_id}


def test_lift_is_one_when_group_matches_overall_exactly():
    assert lib.lift(0.25, 0.25) == 1.0


def test_lift_above_one_means_over_represented():
    assert lib.lift(0.50, 0.25) == 2.0


def test_lift_is_none_when_overall_rate_is_zero():
    """Undefined, not infinite — a failure type that never happens overall
    has no meaningful 'how much more common here' ratio."""
    assert lib.lift(0.10, 0.0) is None


def test_lift_of_zero_is_reported_as_zero_not_falsy_empty():
    """A group with NO occurrences of a common failure type is a real,
    reportable 0.0 lift — not the same as 'undefined'."""
    assert lib.lift(0.0, 0.25) == 0.0


def test_breakdown_by_groups_and_counts_correctly():
    rows = [
        _row("grounded_correct", "q1"), _row("grounded_correct", "q1"),
        _row("generation_failure", "q2"),
    ]
    result = lib.breakdown_by(rows, lambda r: r["question_id"])
    assert result["q1"]["n_observations"] == 2
    assert result["q1"]["n_questions"] == 1
    assert result["q1"]["counts"]["grounded_correct"] == 2
    assert result["q1"]["rates"]["grounded_correct"] == 1.0
    assert result["q2"]["rates"]["generation_failure"] == 1.0


def test_breakdown_rates_cover_every_taxonomy_label_even_at_zero():
    """A label with zero occurrences must still be a 0.0 rate, not missing —
    a missing key would break any downstream code assuming full coverage."""
    rows = [_row("grounded_correct")]
    result = lib.breakdown_by(rows, lambda r: "all")
    assert set(result["all"]["rates"]) == set(FAILURE_LABELS)
    assert result["all"]["rates"]["retrieval_failure_hallucinated"] == 0.0


def test_overall_rates_sum_to_one():
    rows = [_row("grounded_correct"), _row("generation_failure"),
            _row("retrieval_failure_honest"), _row("retrieval_failure_honest")]
    rates = lib.overall_rates(rows)
    assert abs(sum(rates.values()) - 1.0) < 1e-9


def test_question_to_document_strips_the_annual_report_suffix():
    evidence = [
        {"question_id": "q1", "relevant_document": "ecoplast_2025_26_annual_report.pdf"},
        {"question_id": "q2", "relevant_document": "mahindra_2024_25_annual_report.pdf"},
    ]
    mapping = lib.question_to_document(evidence)
    assert mapping["q1"] == "ecoplast"
    assert mapping["q2"] == "mahindra"


def test_question_to_document_picks_first_alphabetically_when_multiple():
    """A question whose evidence spans two documents must resolve to ONE
    document deterministically, not depend on dict/set ordering."""
    evidence = [
        {"question_id": "q1", "relevant_document": "zeta_2025_26_annual_report.pdf"},
        {"question_id": "q1", "relevant_document": "alpha_2025_26_annual_report.pdf"},
    ]
    mapping = lib.question_to_document(evidence)
    assert mapping["q1"] == "alpha"
