"""Tests for the Phase 7A chunk-size experiment's pure logic.

No API key, no index, no PDFs read — everything here is either a synthetic
fixture or a filesystem operation on tmp_path. The group-aware scoring rules
themselves (max-within-group, mode across groups, union span coverage) are
already covered by tests/test_evaluation.py; this file covers what is new to
Phase 7A: config isolation, result-file isolation, the selection rule, the
gold-set fail-fast checks, and the ban on the historical 31-row snapshot.
"""

import csv
import inspect
from pathlib import Path

import pytest

import scripts.build_index as build_index
import scripts.phase7a_lib as lib


# ==========================================================================
# CLI / config parameter isolation
# ==========================================================================
def test_cli_defaults_match_ingestion_constants():
    """A bare invocation must behave exactly as it did before the CLI existed."""
    from src.ingestion import CHUNK_OVERLAP, CHUNK_SIZE

    args = build_index.build_parser().parse_args([])
    assert args.chunk_size == CHUNK_SIZE
    assert args.overlap == CHUNK_OVERLAP


def test_cli_overrides_do_not_touch_module_constants():
    """Sweeping chunk_size via the CLI must never mutate src.ingestion's
    constants — two configs run in the same process must not see each
    other's setting."""
    from src.ingestion import CHUNK_SIZE

    args = build_index.build_parser().parse_args(["--chunk-size", "300"])
    assert args.chunk_size == 300
    assert build_index.CHUNK_SIZE == CHUNK_SIZE  # untouched


@pytest.mark.parametrize("size", [300, 500, 600, 1000])
def test_cli_accepts_every_phase7a_chunk_size(size):
    args = build_index.build_parser().parse_args(["--chunk-size", str(size), "--overlap", "50"])
    assert args.chunk_size == size
    assert args.overlap == 50


# ==========================================================================
# Gold-set integrity — fail fast, never silently adapt
# ==========================================================================
def test_gold_set_matches_expected_counts_today():
    """The counts this experiment was explicitly told to expect."""
    lib.check_gold_set_integrity()  # must not raise


def test_integrity_check_rejects_wrong_question_count(monkeypatch):
    monkeypatch.setattr(lib, "load_questions", lambda: [{"question_id": "q1"}])
    with pytest.raises(SystemExit, match="expected 25 questions"):
        lib.check_gold_set_integrity()


def test_integrity_check_rejects_wrong_group_count(monkeypatch):
    fake_rows = [
        {"question_id": "q1", "group_id": "g1", "evidence_id": "e1"},
        {"question_id": "q1", "group_id": "g2", "evidence_id": "e2"},
    ]
    # Match the row count so the check actually reaches the GROUP-count
    # assertion instead of failing earlier on row count.
    monkeypatch.setattr(lib, "EXPECTED_EVIDENCE_ROW_COUNT", len(fake_rows))
    monkeypatch.setattr(lib, "load_evidence_rows", lambda: fake_rows)
    monkeypatch.setattr(lib, "load_span_rows", lambda: fake_rows)  # keep row-count check happy
    with pytest.raises(SystemExit, match="evidence groups"):
        lib.check_gold_set_integrity()


def test_integrity_check_rejects_orphaned_evidence(monkeypatch):
    monkeypatch.setattr(lib, "EXPECTED_QUESTION_COUNT", 1)
    monkeypatch.setattr(lib, "EXPECTED_EVIDENCE_ROW_COUNT", 1)
    monkeypatch.setattr(lib, "EXPECTED_EVIDENCE_GROUP_COUNT", 1)
    monkeypatch.setattr(lib, "load_questions", lambda: [{"question_id": "q1"}])
    monkeypatch.setattr(lib, "load_evidence_rows", lambda: [
        {"question_id": "q999", "group_id": "g1", "evidence_id": "e1"},
    ])
    monkeypatch.setattr(lib, "load_span_rows", lambda: [
        {"question_id": "q999", "group_id": "g1", "evidence_id": "e1"},
    ])
    with pytest.raises(SystemExit, match="unknown question_id"):
        lib.check_gold_set_integrity()


# ==========================================================================
# Reachability primitive
# ==========================================================================
def test_chunks_needed_for_span_counts_the_easiest_path():
    from src.evaluation import GoldSpan
    from src.ingestion import Chunk

    span = GoldSpan("e1", "q1", "doc.pdf", start_char=90, end_char=110)
    chunks = [
        Chunk("a", "doc.pdf", 0, [1], start_char=0, end_char=100),
        Chunk("b", "doc.pdf", 1, [1], start_char=100, end_char=200),
    ]
    assert lib._chunks_needed_for_span(span, chunks) == 2


def test_chunks_needed_for_span_is_unreachable_sentinel_when_no_chunk_touches_it():
    from src.evaluation import GoldSpan
    from src.ingestion import Chunk

    span = GoldSpan("e1", "q1", "doc.pdf", start_char=900, end_char=1000)
    chunks = [Chunk("a", "doc.pdf", 0, [1], start_char=0, end_char=100)]
    assert lib._chunks_needed_for_span(span, chunks) == 99


# ==========================================================================
# Per-configuration result isolation
# ==========================================================================
def test_upsert_config_rows_does_not_disturb_other_configs(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "CONFIGS_CSV", tmp_path / "configs.csv")

    row = lambda k, cov: {"k": k, "document_recall": 1.0, "gold_span_any_recall": 1.0,
                          "gold_span_coverage": cov, "legacy_any_evidence_recall": 1.0,
                          "legacy_evidence_coverage": cov, "chunk_overlap": 50,
                          "embedding_model": "m", "distance_metric": "cosine",
                          "chunk_count": 100, "index_size_mb": 1.0, "build_time_seconds": 1.0,
                          "legacy_unfindable_count": 0, "span_unreachable_groups": 0,
                          "groups_need_1_chunk": 1, "groups_need_2_chunks": 0,
                          "groups_need_3plus_chunks": 0}

    lib.upsert_config_rows(500, [row(5, 0.5)])
    lib.upsert_config_rows(300, [row(5, 0.3)])
    result = lib.upsert_config_rows(500, [row(5, 0.9)])  # re-run 500

    by_size = {(r["chunk_size"], r["k"]): r["gold_span_coverage"] for r in result}
    assert by_size[("500", "5")] == "0.9"   # replaced
    assert by_size[("300", "5")] == "0.3"   # untouched


def test_upsert_rank_rows_keyed_on_chunk_size_and_question_not_chunk_size_alone(tmp_path, monkeypatch):
    """A key of chunk_size alone would collapse 25 questions into 1 row."""
    monkeypatch.setattr(lib, "RANKS_CSV", tmp_path / "ranks.csv")

    rows_500 = [
        {"question_id": f"q{i}", "difficulty": "easy", "question_type": "numeric",
         "evidence_mode": "all", "first_rank": i, "inspected_depth": 200}
        for i in range(1, 26)
    ]
    result = lib.upsert_rank_rows(500, rows_500)
    assert len(result) == 25

    # Re-running 500 with different values must replace all 25, not append.
    result2 = lib.upsert_rank_rows(500, rows_500)
    assert len(result2) == 25


def test_upsert_rank_rows_isolates_configs(tmp_path, monkeypatch):
    monkeypatch.setattr(lib, "RANKS_CSV", tmp_path / "ranks.csv")
    row = lambda qid: {"question_id": qid, "difficulty": "easy", "question_type": "numeric",
                       "evidence_mode": "all", "first_rank": 1, "inspected_depth": 200}

    lib.upsert_rank_rows(500, [row("q1")])
    result = lib.upsert_rank_rows(300, [row("q1")])
    assert len(result) == 2  # one row per (chunk_size, question), not overwritten


# ==========================================================================
# Selection rule — tie-breakers applied mechanically, in the pre-registered order
# ==========================================================================
def _config_row(chunk_size, k, coverage, any_recall=0.5, chunk_count=20000):
    return {"chunk_size": str(chunk_size), "k": str(k),
           "gold_span_coverage": str(coverage), "gold_span_any_recall": str(any_recall),
           "chunk_count": str(chunk_count)}


def _rank_row(chunk_size, qid, rank):
    return {"chunk_size": str(chunk_size), "question_id": qid, "first_rank": str(rank)}


def test_selection_picks_highest_coverage_at_5():
    rows = [
        *[_config_row(300, k, 0.30) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.50) for k in (1, 3, 5, 10)],
    ]
    winner, _ = lib.select_winning_config(rows, [])
    assert winner == "500"


def test_tiebreak_falls_through_to_any_recall_when_coverage_ties():
    rows = [
        *[_config_row(300, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.40, any_recall=0.80) for k in (1, 3, 5, 10)],
    ]
    winner, _ = lib.select_winning_config(rows, [])
    assert winner == "500"


def test_tiebreak_falls_through_to_median_rank_when_coverage_and_recall_tie():
    rows = [
        *[_config_row(300, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
    ]
    ranks = [
        _rank_row(300, "q1", 20), _rank_row(300, "q2", 20),
        _rank_row(500, "q1", 2), _rank_row(500, "q2", 2),
    ]
    winner, _ = lib.select_winning_config(rows, ranks)
    assert winner == "500"  # lower median rank wins


def test_tiebreak_falls_through_to_coverage_at_3():
    rows = [
        *[_config_row(300, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
    ]
    # Override K=3 rows with different coverage.
    for row in rows:
        if row["chunk_size"] == "500" and row["k"] == "3":
            row["gold_span_coverage"] = "0.70"
        if row["chunk_size"] == "300" and row["k"] == "3":
            row["gold_span_coverage"] = "0.20"
    ranks = [_rank_row(300, "q1", 5), _rank_row(500, "q1", 5)]  # tie on median too
    winner, _ = lib.select_winning_config(rows, ranks)
    assert winner == "500"


def test_final_tiebreak_prefers_smaller_index():
    rows = [
        *[_config_row(1000, k, 0.40, any_recall=0.60, chunk_count=10000) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.40, any_recall=0.60, chunk_count=22832) for k in (1, 3, 5, 10)],
    ]
    ranks = [_rank_row(1000, "q1", 5), _rank_row(500, "q1", 5)]
    winner, _ = lib.select_winning_config(rows, ranks)
    assert winner == "1000"  # fewer chunks


def test_selection_ignores_document_recall_entirely():
    """Document Recall must not appear anywhere in the sort key."""
    source = inspect.getsource(lib.select_winning_config)
    assert "document_recall" not in source


def test_selection_handles_a_config_with_no_ranks_found():
    """A config with zero gold-span hits must lose tie-breaks, not crash."""
    rows = [
        *[_config_row(300, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
        *[_config_row(500, k, 0.40, any_recall=0.60) for k in (1, 3, 5, 10)],
    ]
    ranks = [_rank_row(500, "q1", 5)]  # 300 has no rank rows at all
    winner, ranking = lib.select_winning_config(rows, ranks)
    assert winner == "500"
    assert set(ranking) == {"300", "500"}


# ==========================================================================
# The 31-row historical snapshot must never be reachable from Phase 7A code
# ==========================================================================
def test_phase7a_modules_never_reference_the_pregroups_snapshot():
    import scripts.measure_phase7a as measure_phase7a

    for module in (lib, measure_phase7a):
        source = inspect.getsource(module)
        assert "pre-groups" not in source.lower()
        assert "scratchpad" not in source.lower()
        assert "PRE_GROUPS_EVIDENCE_CSV" not in source


def test_phase7a_evidence_loaders_read_the_current_35_row_file():
    assert lib.EVIDENCE_CSV == Path("data/evaluation/evidence.csv")
    assert lib.SPANS_CSV == Path("data/evaluation/evidence_spans.csv")
    rows = lib.load_evidence_rows()
    assert len(rows) == 35


# ==========================================================================
# score_configuration wiring — a fake retriever, no index needed
# ==========================================================================
def test_score_configuration_produces_one_row_per_k_and_one_rank_row_per_question():
    from src.evaluation import Evidence, GoldSpan
    from src.retrieval import RetrievedChunk

    questions = [{"question_id": "q1", "question": "x?", "difficulty": "easy",
                 "question_type": "numeric", "evidence_mode": "all"}]
    spans = {"q1": [GoldSpan("e1", "q1", "d.pdf", 0, 10, group_id="g1")]}
    legacy = {"q1": [Evidence("e1", "q1", "d.pdf", "1", "hello")]}

    def fake_retrieve(_text, k):
        return [RetrievedChunk("hello world", "d.pdf", 0, [1], 0.9,
                               start_char=0, end_char=15)][:k]

    per_k, rank_rows = lib.score_configuration(questions, spans, legacy, fake_retrieve)

    assert {row["k"] for row in per_k} == {1, 3, 5, 10}
    assert len(rank_rows) == 1
    assert rank_rows[0]["question_id"] == "q1"
