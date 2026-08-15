"""Tests for Phase 9's pure logic. No API key, no index, no generation calls —
everything here re-aggregates synthetic rows shaped like the real CSVs.
"""

import inspect

import pytest

import scripts.phase9_lib as lib


def _row(chunk_size=500, run_index=1, input_tokens=800, output_tokens=20,
         latency=1.0, correct=0, faithful=0, relevant=1, evidence_hit=0,
         failure_label="retrieval_failure_honest"):
    return {
        "chunk_size": str(chunk_size), "run_index": str(run_index),
        "question_id": "q001", "difficulty": "easy", "question_type": "numeric",
        "evidence_mode": "all", "evidence_hit": evidence_hit, "abstained": 1 - correct,
        "correct": correct, "faithful": faithful, "relevant": relevant,
        "failure_label": failure_label, "input_tokens": str(input_tokens),
        "output_tokens": str(output_tokens), "cost_usd": "0.0", "latency_seconds": str(latency),
        "answer": "x",
    }


def _cast(rows):
    """Mimic load_generation_rows()'s int/float casting on hand-built rows."""
    for row in rows:
        row["input_tokens"] = int(row["input_tokens"])
        row["output_tokens"] = int(row["output_tokens"])
        row["latency_seconds"] = float(row["latency_seconds"])
    return rows


# ==========================================================================
# Percentage-difference calculation
# ==========================================================================
def test_pct_diff_computes_relative_change():
    assert lib.pct_diff(120, 100) == pytest.approx(0.20)
    assert lib.pct_diff(80, 100) == pytest.approx(-0.20)


def test_pct_diff_is_none_when_baseline_is_zero():
    """Undefined, not infinite — a percentage change FROM zero has no ratio."""
    assert lib.pct_diff(50, 0) is None


def test_pct_diff_zero_when_values_equal():
    assert lib.pct_diff(100, 100) == 0.0


# ==========================================================================
# Config grouping
# ==========================================================================
def test_rows_for_config_isolates_correctly():
    rows = [_row(chunk_size=500), _row(chunk_size=600), _row(chunk_size=500)]
    assert len(lib.rows_for_config(rows, 500)) == 2
    assert len(lib.rows_for_config(rows, 600)) == 1


def test_rows_by_run_groups_correctly():
    rows = [_row(run_index=1), _row(run_index=1), _row(run_index=2)]
    by_run = lib.rows_by_run(rows)
    assert set(by_run) == {1, 2}
    assert len(by_run[1]) == 2
    assert len(by_run[2]) == 1


# ==========================================================================
# Token aggregation
# ==========================================================================
def test_token_stats_totals_and_averages():
    rows = _cast([_row(input_tokens=100, output_tokens=10),
                  _row(input_tokens=200, output_tokens=20)])
    stats = lib.token_stats(rows)
    assert stats["n"] == 2
    assert stats["total_input_tokens"] == 300
    assert stats["mean_input_tokens"] == 150
    assert stats["median_input_tokens"] == 150
    assert stats["total_output_tokens"] == 30
    assert stats["total_tokens"] == 330


def test_tokens_by_run_sums_within_each_run_only():
    rows = _cast([_row(run_index=1, input_tokens=100), _row(run_index=1, input_tokens=50),
                  _row(run_index=2, input_tokens=999)])
    by_run = lib.tokens_by_run(rows)
    assert by_run[1]["input_tokens"] == 150
    assert by_run[2]["input_tokens"] == 999


def test_tokens_per_success_divides_total_input_by_successes():
    rows = _cast([_row(input_tokens=1000, correct=1), _row(input_tokens=1000, correct=0)])
    assert lib.tokens_per_success(rows, "correct") == 2000.0  # both rows' tokens / 1 success


# ==========================================================================
# Zero-denominator handling
# ==========================================================================
def test_tokens_per_success_is_none_with_zero_successes():
    """Reporting 0 here would falsely imply the tokens were free."""
    rows = _cast([_row(correct=0), _row(correct=0)])
    assert lib.tokens_per_success(rows, "correct") is None


def test_per_1000_input_tokens_is_zero_with_no_tokens_not_a_crash():
    rows = _cast([_row(input_tokens=0, correct=1)])
    assert lib.per_1000_input_tokens(rows, "correct") == 0.0


def test_per_second_latency_is_zero_with_zero_latency_not_a_crash():
    rows = _cast([_row(latency=0.0, correct=1)])
    assert lib.per_second_latency(rows, "correct") == 0.0


def test_cost_usd_is_none_without_verified_pricing():
    """The core guard: no pricing object in, no dollar figure out — ever."""
    assert lib.cost_usd(1000, 100, pricing=None) is None


# ==========================================================================
# Latency aggregation
# ==========================================================================
def test_latency_stats_basic_shape():
    rows = _cast([_row(latency=1.0), _row(latency=2.0), _row(latency=3.0)])
    stats = lib.latency_stats(rows)
    assert stats["n"] == 3
    assert stats["mean"] == 2.0
    assert stats["median"] == 2.0
    assert stats["min"] == 1.0
    assert stats["max"] == 3.0
    assert stats["total_wall_clock"] == 6.0
    assert stats["stdev"] > 0


def test_latency_stats_single_row_has_zero_stdev_not_a_crash():
    """statistics.stdev() raises on n=1 — must be guarded, not left to crash."""
    rows = _cast([_row(latency=1.5)])
    stats = lib.latency_stats(rows)
    assert stats["stdev"] == 0.0


def test_latency_by_run_computes_independently_per_run():
    rows = _cast([_row(run_index=1, latency=1.0), _row(run_index=1, latency=1.0),
                  _row(run_index=2, latency=5.0), _row(run_index=2, latency=5.0)])
    by_run = lib.latency_by_run(rows)
    assert by_run[1]["mean"] == 1.0
    assert by_run[2]["mean"] == 5.0


# ==========================================================================
# No hard-coded monetary pricing silently entering calculations
# ==========================================================================
def test_no_module_level_pricing_constants_in_phase9_lib():
    """Regression guard: token->dollar conversion must only ever happen
    through an explicit VerifiedPricing instance passed by the caller — never
    a bare float constant living in this module."""
    source = inspect.getsource(lib)
    assert "0.15" not in source
    assert "0.60" not in source
    assert "COST_PER_MTOK" not in source


def test_cost_usd_requires_an_explicit_pricing_object():
    """The function signature itself has no default price to fall back to."""
    sig = inspect.signature(lib.cost_usd)
    assert sig.parameters["pricing"].default is None


def test_verified_pricing_carries_its_own_provenance():
    """A price with no source/date attached is exactly the 'stale constant'
    failure mode Phase 9 was told to avoid."""
    pricing = lib.VerifiedPricing(
        model="gpt-4o-mini", input_cost_per_mtok=0.15, output_cost_per_mtok=0.60,
        date_checked="2026-08-15", source="https://platform.openai.com/docs/pricing",
    )
    assert pricing.date_checked and pricing.source
    assert lib.cost_usd(1_000_000, 1_000_000, pricing) == pytest.approx(0.75)
