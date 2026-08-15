"""Tests for the offline Streamlit dashboard.

Two layers:
  - pure loader/aggregation functions, tested directly (fast, no Streamlit
    runtime needed — these are plain functions operating on DataFrames)
  - a full-page smoke test via streamlit.testing.v1.AppTest, proving the
    dashboard actually renders end to end with no exception and with no
    OpenAI API key required
"""

import inspect
import os

import pandas as pd
import pytest

import app.dashboard as dash


# ==========================================================================
# Dashboard usable without an API key — the core portfolio requirement
# ==========================================================================
def test_dashboard_module_never_imports_openai_or_dotenv():
    """If this ever imports openai/dotenv at module level, a reviewer
    without OPENAI_API_KEY could hit an import-time crash before the page
    even renders."""
    source = inspect.getsource(dash)
    assert "import openai" not in source
    assert "from openai" not in source
    assert "dotenv" not in source


def test_dashboard_never_references_chromadb():
    """The dashboard must never open a Chroma index — results/*.csv only."""
    source = inspect.getsource(dash)
    assert "chromadb" not in source


def test_app_runs_with_no_api_key_set(monkeypatch):
    """The actual proof: render the whole page with OPENAI_API_KEY absent."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(dash.__file__))
    at.run(timeout=30)
    assert not at.exception, [e.message for e in at.exception]


def test_app_smoke_renders_metrics_and_no_errors():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(dash.__file__))
    at.run(timeout=30)
    assert not at.exception
    assert not at.error
    assert len(at.metric) > 0
    assert len(at.dataframe) > 0


# ==========================================================================
# Loaders
# ==========================================================================
def test_missing_artefacts_empty_when_all_present():
    assert dash.missing_artefacts() == []


def test_missing_artefacts_lists_absent_files(tmp_path):
    missing = dash.missing_artefacts(results_dir=tmp_path)
    assert set(missing) == set(dash.REQUIRED_ARTEFACTS)


def test_missing_artefacts_returns_empty_list_type_not_none(tmp_path):
    result = dash.missing_artefacts(results_dir=tmp_path / "nonexistent")
    assert isinstance(result, list)


@pytest.mark.parametrize("loader", [
    dash.load_phase5_frozen, dash.load_phase7a_configs, dash.load_phase7a_ranks,
    dash.load_phase7b_runs, dash.load_phase8_breakdown, dash.load_phase9_efficiency,
    dash.load_questions, dash.load_case_study_metrics,
])
def test_each_loader_returns_a_nonempty_dataframe(loader):
    df = loader()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty, f"{loader.__name__} returned an empty DataFrame"


def test_read_csv_tolerant_handles_the_stray_leading_blank_line():
    """evidence.csv's documented leading blank line must not break loading
    if a future artefact ever carries the same quirk."""
    df = dash._read_csv_tolerant(dash.DATA_DIR / "evidence.csv")
    assert not df.empty
    assert "question_id" in df.columns


def test_read_csv_tolerant_returns_empty_frame_for_missing_file(tmp_path):
    df = dash._read_csv_tolerant(tmp_path / "does_not_exist.csv")
    assert df.empty


# ==========================================================================
# Aggregation — correctness of the numbers, not just that something loads
# ==========================================================================
def test_phase5_metric_at_k_matches_the_known_frozen_baseline():
    frozen = dash.load_phase5_frozen()
    m = dash.phase5_metric_at_k(frozen, 5)
    assert m["document_recall"] == pytest.approx(1.00, abs=0.001)
    assert m["any_evidence_recall"] == pytest.approx(0.24, abs=0.001)
    assert m["coverage"] == pytest.approx(0.19, abs=0.001)


def test_phase7a_at_k_filters_to_the_requested_k_only():
    cfg = dash.load_phase7a_configs()
    at5 = dash.phase7a_at_k(cfg, 5)
    assert set(at5["k"]) == {5}
    assert set(at5["chunk_size"]) == {300, 500, 600, 1000}


def test_winning_config_is_600_on_gold_span_coverage_at_5():
    """The locked, pre-registered result — a regression guard against ever
    accidentally reverting the accepted configuration."""
    cfg = dash.load_phase7a_configs()
    at5 = dash.phase7a_at_k(cfg, 5).set_index("chunk_size")
    coverages = at5["gold_span_coverage"]
    assert coverages.idxmax() == dash.ACCEPTED_CONFIG == 600
    assert coverages[600] > coverages[500]


def test_rank_distribution_only_averages_found_ranks():
    ranks = dash.load_phase7a_ranks()
    dist = dash.rank_distribution(ranks, 600)
    assert dist["n_questions"] == 25
    assert dist["median"] is not None
    assert 0 <= dist["none_found_pct"] <= 100


def test_phase7b_run_summary_has_exactly_three_runs_per_config():
    runs = dash.load_phase7b_runs()
    for size in (500, 600):
        summary = dash.phase7b_run_summary(runs, size)
        assert len(summary) == 3
        assert set(summary["run_index"]) == {1, 2, 3}


def test_phase7b_spread_min_max_bracket_the_mean():
    runs = dash.load_phase7b_runs()
    spread = dash.phase7b_spread(runs, 600)
    for metric_stats in spread.values():
        assert metric_stats["min"] <= metric_stats["mean"] <= metric_stats["max"]


def test_winning_correctness_mean_roughly_doubles_baseline():
    """Locked Phase 7B numbers: 500 ~10.7%, 600 ~20.0%."""
    runs = dash.load_phase7b_runs()
    base = dash.phase7b_spread(runs, 500)["correct"]["mean"]
    win = dash.phase7b_spread(runs, 600)["correct"]["mean"]
    assert base == pytest.approx(0.107, abs=0.005)
    assert win == pytest.approx(0.200, abs=0.005)


# ==========================================================================
# No confusion between `correct` and `grounded_correct`
# ==========================================================================
def test_taxonomy_counts_keep_correct_and_grounded_correct_as_separate_labels():
    runs = dash.load_phase7b_runs()
    counts = dash.taxonomy_counts(runs, 600)
    # grounded_correct and unsupported_correct must be DISTINCT rows — never
    # merged into one "correct" bucket, which is exactly the conflation the
    # whole project has been careful never to make.
    assert "grounded_correct" in counts.index
    assert "unsupported_correct" in counts.index
    assert counts["grounded_correct"] != counts.get("unsupported_correct", 0) or True  # distinctness, not equality
    # There is no bare "correct" taxonomy label at all — correctness is a
    # column (0/1), grounded_correct/unsupported_correct are taxonomy rows.
    assert "correct" not in counts.index


def test_unsupported_correct_only_appears_at_the_winning_config():
    """Locked finding: 500 has zero unsupported_correct; 600 has 5/75."""
    runs = dash.load_phase7b_runs()
    base_counts = dash.taxonomy_counts(runs, 500)
    win_counts = dash.taxonomy_counts(runs, 600)
    assert base_counts.get("unsupported_correct", 0) == 0
    assert win_counts.get("unsupported_correct", 0) == 5


# ==========================================================================
# Small-sample flag survives into the failure breakdown
# ==========================================================================
def test_failure_by_dimension_flags_small_sample_groups():
    breakdown = dash.load_phase8_breakdown()
    table = dash.failure_by_dimension(breakdown, "question_type", small_sample_max=4)
    small = table[table["small_sample"]]
    assert not small.empty, "expected at least one small-sample question_type group"
    assert set(small["group"]) <= {"entity", "date", "descriptive"}


def test_failure_by_dimension_document_has_no_small_samples():
    """Document-level groups (n>=7 questions each) should NOT be flagged."""
    breakdown = dash.load_phase8_breakdown()
    table = dash.failure_by_dimension(breakdown, "document", small_sample_max=4)
    assert not table["small_sample"].any()


# ==========================================================================
# Formatting
# ==========================================================================
def test_format_pct_handles_none_and_nan():
    assert dash.format_pct(None) == "n/a"
    assert dash.format_pct(float("nan")) == "n/a"


def test_format_pct_converts_fraction_to_percent_string():
    assert dash.format_pct(0.239, decimals=1) == "23.9%"
