"""Tests for Phase 7B's pure logic — spread computation, the overlap check,
and per-configuration result isolation. No API key, no index, no generation.
"""

import scripts.phase7b_lib as lib


def _rows(correct, faithful, relevant, abstained):
    """Build one run's worth of rows from four rates, n=10, for round numbers."""
    n = 10
    return [
        {"correct": int(i < correct * n), "faithful": int(i < faithful * n),
         "relevant": int(i < relevant * n), "abstained": int(i < abstained * n),
         "failure_label": "grounded_correct"}
        for i in range(n)
    ]


# ==========================================================================
# Rate / spread computation
# ==========================================================================
def test_run_rate_computes_the_fraction():
    rows = _rows(correct=0.6, faithful=1.0, relevant=1.0, abstained=0.0)
    assert lib.run_rate(rows, "correct") == 0.6


def test_summarize_run_reports_taxonomy_counts():
    rows = _rows(correct=0.5, faithful=0.5, relevant=1.0, abstained=0.0)
    summary = lib.summarize_run(rows)
    assert summary["n"] == 10
    assert summary["taxonomy"] == {"grounded_correct": 10}


def test_spread_reports_mean_min_max_range():
    result = lib.spread([0.20, 0.30, 0.28])
    assert result["min"] == 0.20
    assert result["max"] == 0.30
    assert round(result["mean"], 4) == round((0.20 + 0.30 + 0.28) / 3, 4)
    assert round(result["range"], 4) == round(0.10, 4)


def test_spread_of_identical_runs_is_zero():
    """Three runs producing the exact same rate — no noise to report."""
    result = lib.spread([0.24, 0.24, 0.24])
    assert result["range"] == 0.0


def test_config_spread_covers_all_four_headline_metrics():
    summaries = [
        {"correct_rate": 0.1, "faithful_rate": 0.7, "relevant_rate": 0.9, "abstain_rate": 0.5},
        {"correct_rate": 0.2, "faithful_rate": 0.8, "relevant_rate": 0.9, "abstain_rate": 0.4},
        {"correct_rate": 0.15, "faithful_rate": 0.75, "relevant_rate": 1.0, "abstain_rate": 0.5},
    ]
    result = lib.config_spread(summaries)
    assert set(result) == {"correct_rate", "faithful_rate", "relevant_rate", "abstain_rate"}
    assert result["correct_rate"]["min"] == 0.1
    assert result["correct_rate"]["max"] == 0.2


# ==========================================================================
# Range-overlap check — a plain auditable check, not a significance test
# ==========================================================================
def test_ranges_overlap_when_they_share_any_point():
    assert lib.ranges_overlap(0.10, 0.30, 0.25, 0.40) is True


def test_ranges_do_not_overlap_when_cleanly_separated():
    assert lib.ranges_overlap(0.10, 0.20, 0.30, 0.40) is False


def test_ranges_overlap_at_a_shared_boundary():
    """Touching exactly at the edge counts as overlapping, not separated."""
    assert lib.ranges_overlap(0.10, 0.20, 0.20, 0.30) is True


def test_ranges_overlap_is_symmetric():
    a = lib.ranges_overlap(0.10, 0.20, 0.30, 0.40)
    b = lib.ranges_overlap(0.30, 0.40, 0.10, 0.20)
    assert a == b


# ==========================================================================
# Per-configuration result isolation
# ==========================================================================
def _raw_row(qid="q001", correct=1):
    return {"question_id": qid, "difficulty": "easy", "question_type": "numeric",
           "evidence_mode": "all", "evidence_hit": 1, "abstained": 0, "correct": correct,
           "faithful": 1, "relevant": 1, "failure_label": "grounded_correct",
           "input_tokens": 100, "output_tokens": 20, "cost_usd": 0.0001,
           "latency_seconds": 1.0, "answer": "x", "run_index": 1}


def test_upsert_raw_rows_isolates_configs(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "RAW_CSV", tmp_path / "raw.csv")

    lib.upsert_raw_rows(500, [_raw_row(correct=1)])
    lib.upsert_raw_rows(600, [_raw_row(correct=0)])
    result = lib.upsert_raw_rows(500, [_raw_row(correct=1), {**_raw_row(qid="q002"), "run_index": 2}])

    sizes = {row["chunk_size"] for row in result}
    assert sizes == {"500", "600"}
    five_hundred = [r for r in result if r["chunk_size"] == "500"]
    assert len(five_hundred) == 2  # replaced with the new 2-row set, not appended to
    six_hundred = [r for r in result if r["chunk_size"] == "600"]
    assert len(six_hundred) == 1   # untouched by the 500 re-run


def test_rows_by_run_groups_correctly():
    rows = [
        {"run_index": "1", "question_id": "q1", "correct": "1", "faithful": "1",
         "relevant": "1", "abstained": "0"},
        {"run_index": "2", "question_id": "q1", "correct": "0", "faithful": "1",
         "relevant": "1", "abstained": "1"},
    ]
    by_run = lib.rows_by_run(rows)
    assert set(by_run) == {1, 2}
    assert by_run[1][0]["correct"] == 1  # cast to int
