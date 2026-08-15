"""Shared logic for the Phase 7A chunk-size experiment.

Kept separate from scripts/measure_phase7a.py so the pure-logic pieces —
gold-set integrity, group reachability, the selection rule, per-config CSV
upsert — are testable without an index, an API key, or a live retrieval
call. Only the functions that actually call retrieve() need the network.

Phase 7A uses the CURRENT gold set (25 questions / 35 evidence rows / 30
groups), never the historical 31-row snapshot that the Phase 5 reproducibility
gate used — that snapshot existed for exactly one purpose (reproducing the
frozen baseline) and has no business here.
"""

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

from src.evaluation import (
    DEFAULT_EVIDENCE_MODE,
    Evidence,
    GoldSpan,
    any_evidence_at_k,
    document_recall_at_k,
    evidence_coverage_at_k,
    first_gold_span_rank,
    gold_span_any_recall_at_k,
    gold_span_coverage_at_k,
    unfindable_evidence,
)
from src.ingestion import Chunk, load_pdf_pages, split_into_chunks
from src.retrieval import RetrievedChunk

# --------------------------------------------------------------------------
# Fixed experiment parameters — same corpus, embedding model, overlap and
# distance for every configuration. Only chunk_size varies.
# --------------------------------------------------------------------------
DOCUMENTS_DIR = Path("data/documents")
QUESTIONS_CSV = Path("data/evaluation/questions.csv")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
SPANS_CSV = Path("data/evaluation/evidence_spans.csv")

CONFIGS_CSV = Path("results/phase7a_retrieval_configs.csv")
CONFIGS_MD = Path("results/phase7a_retrieval_configs.md")
RANKS_CSV = Path("results/phase7a_first_span_ranks.csv")

K_VALUES = (1, 3, 5, 10)
RANK_DEPTH = 200  # inspected retrieval depth for the first-gold-span-rank scan
CHUNK_SIZES = (300, 500, 600, 1000)

EXPECTED_QUESTION_COUNT = 25
EXPECTED_EVIDENCE_ROW_COUNT = 35
EXPECTED_EVIDENCE_GROUP_COUNT = 30

CONFIG_ROW_FIELDS = [
    "chunk_size", "chunk_overlap", "embedding_model", "distance_metric", "k",
    "document_recall", "gold_span_any_recall", "gold_span_coverage",
    "legacy_any_evidence_recall", "legacy_evidence_coverage",
    "chunk_count", "index_size_mb", "build_time_seconds",
    "legacy_unfindable_count", "span_unreachable_groups",
    "groups_need_1_chunk", "groups_need_2_chunks", "groups_need_3plus_chunks",
]

RANK_ROW_FIELDS = [
    "chunk_size", "question_id", "difficulty", "question_type", "evidence_mode",
    "first_rank", "inspected_depth",
]


# --------------------------------------------------------------------------
# Gold set loading — tolerant of the stray leading blank line documented in
# the Phase 5 reproducibility gate, without ever rewriting the source files.
# --------------------------------------------------------------------------
def _read_rows(path: Path) -> list[dict]:
    lines = [line for line in path.open(encoding="utf-8") if line.strip()]
    return list(csv.DictReader(lines))


def load_questions() -> list[dict]:
    return _read_rows(QUESTIONS_CSV)


def load_evidence_rows() -> list[dict]:
    return _read_rows(EVIDENCE_CSV)


def load_span_rows() -> list[dict]:
    return _read_rows(SPANS_CSV)


def check_gold_set_integrity() -> None:
    """Fail fast rather than silently adapt if the gold set has drifted.

    Every count here is a fact this experiment was explicitly told to expect.
    A silent mismatch would mean every downstream number is computed against
    a gold set nobody signed off on.
    """
    questions = load_questions()
    evidence = load_evidence_rows()
    spans = load_span_rows()

    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_QUESTION_COUNT} questions, found {len(questions)}"
        )
    if len(evidence) != EXPECTED_EVIDENCE_ROW_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_EVIDENCE_ROW_COUNT} evidence rows, found {len(evidence)}"
        )
    if len(spans) != EXPECTED_EVIDENCE_ROW_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_EVIDENCE_ROW_COUNT} evidence_spans rows, found {len(spans)}"
        )

    evidence_groups = {row["group_id"] for row in evidence}
    span_groups = {row["group_id"] for row in spans}
    if len(evidence_groups) != EXPECTED_EVIDENCE_GROUP_COUNT:
        raise SystemExit(
            f"expected {EXPECTED_EVIDENCE_GROUP_COUNT} evidence groups, "
            f"found {len(evidence_groups)}"
        )
    if evidence_groups != span_groups:
        raise SystemExit(
            f"evidence.csv and evidence_spans.csv disagree on group_id set: "
            f"{evidence_groups ^ span_groups}"
        )

    question_ids = {row["question_id"] for row in questions}
    evidence_qids = {row["question_id"] for row in evidence}
    orphaned = evidence_qids - question_ids
    if orphaned:
        raise SystemExit(f"evidence rows reference unknown question_id(s): {orphaned}")

    evidence_ids = {row["evidence_id"] for row in evidence}
    span_ids = {row["evidence_id"] for row in spans}
    if evidence_ids != span_ids:
        raise SystemExit(
            f"evidence.csv and evidence_spans.csv disagree on evidence_id set: "
            f"{evidence_ids ^ span_ids}"
        )


def build_legacy_evidence() -> dict[str, list[Evidence]]:
    """Flat, ungrouped Evidence per question — the CURRENT evidence.csv.

    This is the "legacy" text-matching ruler from Phase 5/6, re-pointed at
    the 35-row gold set. It is deliberately NOT the 31-row snapshot: that
    snapshot's only job was reproducing the frozen baseline.
    """
    by_question: dict[str, list[Evidence]] = {}
    for row in load_evidence_rows():
        by_question.setdefault(row["question_id"], []).append(
            Evidence(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                relevant_document=row["relevant_document"],
                relevant_pages=row["relevant_pages"],
                evidence_text=row["evidence_text"],
            )
        )
    return by_question


def build_gold_spans() -> dict[str, list[GoldSpan]]:
    """Group-aware GoldSpans per question, from the derived evidence_spans.csv."""
    by_question: dict[str, list[GoldSpan]] = {}
    for row in load_span_rows():
        by_question.setdefault(row["question_id"], []).append(
            GoldSpan(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                source_document=row["source_document"],
                start_char=int(row["start_char"]),
                end_char=int(row["end_char"]),
                group_id=row["group_id"],
            )
        )
    return by_question


def gold_span_groups() -> dict[str, list[GoldSpan]]:
    """All gold spans grouped by group_id, flattened across questions."""
    groups: dict[str, list[GoldSpan]] = {}
    for row in load_span_rows():
        groups.setdefault(row["group_id"], []).append(
            GoldSpan(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                source_document=row["source_document"],
                start_char=int(row["start_char"]),
                end_char=int(row["end_char"]),
                group_id=row["group_id"],
            )
        )
    return groups


# --------------------------------------------------------------------------
# Static, CPU-only diagnostics — one local (non-embedded) chunking pass per
# configuration. No API calls, so these run even if span_unreachable_groups
# turns out to force an abort before any retrieval happens.
# --------------------------------------------------------------------------
@dataclass
class LocalChunking:
    """One configuration's chunks, computed locally (no embeddings)."""

    chunk_size: int
    overlap: int
    total_chunk_count: int
    chunks_by_document: dict[str, list[Chunk]]


def chunk_locally(chunk_size: int, overlap: int, documents_dir: Path = DOCUMENTS_DIR) -> LocalChunking:
    """Re-chunk every PDF in memory, for verification and static diagnostics.

    This is a pure function of (chunk_size, overlap, the PDFs) — identical to
    what build_index() sliced when it built the real index — so its total
    count is the ground truth an index's collection.count() is checked
    against, and its .text values are what the legacy text ruler runs on.
    """
    chunks_by_document: dict[str, list[Chunk]] = {}
    total = 0
    for path in sorted(documents_dir.glob("*.pdf")):
        chunks = split_into_chunks(load_pdf_pages(path), path.name, chunk_size, overlap)
        chunks_by_document[path.name] = chunks
        total += len(chunks)
    return LocalChunking(chunk_size, overlap, total, chunks_by_document)


def _chunks_needed_for_span(span: GoldSpan, chunks: list[Chunk]) -> int:
    """Fewest CONTIGUOUS chunks whose union fully covers one span.

    99 is the "unreachable" sentinel: no combination of chunks in this
    document covers the span at all, at any length.
    """
    start, end = span.start_char, span.end_char
    touching = sorted(
        (chunk.start_char, chunk.end_char)
        for chunk in chunks
        if chunk.source_document == span.source_document
        and chunk.start_char < end and start < chunk.end_char
    )
    cursor, used = start, 0
    while cursor < end:
        reach = max((chunk_end for chunk_start, chunk_end in touching if chunk_start <= cursor),
                    default=cursor)
        if reach <= cursor:
            return 99
        cursor, used = reach, used + 1
    return used


@dataclass
class ReachabilityReport:
    unreachable_groups: int
    groups_need_1_chunk: int
    groups_need_2_chunks: int
    groups_need_3plus_chunks: int
    legacy_unfindable_count: int


def compute_reachability(local: LocalChunking) -> ReachabilityReport:
    """How hard is each required fact to retrieve, structurally, at this
    chunk size — independent of embeddings or ranking."""
    all_chunks = [chunk for chunks in local.chunks_by_document.values() for chunk in chunks]

    needed = {
        group_id: min(_chunks_needed_for_span(span, all_chunks) for span in alternatives)
        for group_id, alternatives in gold_span_groups().items()
    }
    unreachable = sum(1 for n in needed.values() if n == 99)
    reachable = [n for n in needed.values() if n != 99]

    legacy_evidence = [item for items in build_legacy_evidence().values() for item in items]
    all_texts = [chunk.text for chunk in all_chunks]
    unfindable = unfindable_evidence(legacy_evidence, all_texts)

    return ReachabilityReport(
        unreachable_groups=unreachable,
        groups_need_1_chunk=sum(1 for n in reachable if n == 1),
        groups_need_2_chunks=sum(1 for n in reachable if n == 2),
        groups_need_3plus_chunks=sum(1 for n in reachable if n >= 3),
        legacy_unfindable_count=len(unfindable),
    )


# --------------------------------------------------------------------------
# Retrieval-dependent scoring — needs a built, embedded index.
# --------------------------------------------------------------------------
def score_configuration(
    questions: list[dict],
    spans_by_question: dict[str, list[GoldSpan]],
    legacy_by_question: dict[str, list[Evidence]],
    retrieve_fn,
) -> tuple[list[dict], list[dict]]:
    """Retrieve once per question at RANK_DEPTH, score every K by slicing.

    retrieve_fn(question_text, k) -> list[RetrievedChunk] is injected so tests
    can supply a fake without a live index or an API key.
    """
    per_k_totals = {
        k: {"doc": 0, "span_any": 0, "span_cov": 0.0, "legacy_any": 0, "legacy_cov": 0.0}
        for k in K_VALUES
    }
    rank_rows: list[dict] = []
    n = len(questions)

    for question in questions:
        qid = question["question_id"]
        spans = spans_by_question[qid]
        legacy = legacy_by_question[qid]
        mode = question.get("evidence_mode") or DEFAULT_EVIDENCE_MODE

        retrieved = retrieve_fn(question["question"], RANK_DEPTH)

        for k in K_VALUES:
            per_k_totals[k]["doc"] += int(document_recall_at_k(retrieved, legacy, k))
            per_k_totals[k]["span_any"] += int(gold_span_any_recall_at_k(retrieved, spans, k))
            per_k_totals[k]["span_cov"] += gold_span_coverage_at_k(retrieved, spans, k, mode)
            per_k_totals[k]["legacy_any"] += int(any_evidence_at_k(retrieved, legacy, k))
            per_k_totals[k]["legacy_cov"] += evidence_coverage_at_k(retrieved, legacy, k, mode)

        rank = first_gold_span_rank(retrieved, spans)
        rank_rows.append({
            "question_id": qid,
            "difficulty": question["difficulty"],
            "question_type": question["question_type"],
            "evidence_mode": mode,
            "first_rank": rank if rank is not None else "",
            "inspected_depth": RANK_DEPTH,
        })

    config_rows = [
        {
            "k": k,
            "document_recall": per_k_totals[k]["doc"] / n,
            "gold_span_any_recall": per_k_totals[k]["span_any"] / n,
            "gold_span_coverage": per_k_totals[k]["span_cov"] / n,
            "legacy_any_evidence_recall": per_k_totals[k]["legacy_any"] / n,
            "legacy_evidence_coverage": per_k_totals[k]["legacy_cov"] / n,
        }
        for k in K_VALUES
    ]
    return config_rows, rank_rows


def rank_distribution(ranks: list[int | None]) -> dict:
    found = [r for r in ranks if r is not None]
    n = len(ranks)
    if not found:
        return {"median": None, "mean": None, "min": None, "max": None,
                "none_found_pct": 100.0}
    return {
        "median": statistics.median(found),
        "mean": sum(found) / len(found),
        "min": min(found),
        "max": max(found),
        "none_found_pct": 100.0 * (n - len(found)) / n,
    }


# --------------------------------------------------------------------------
# Per-configuration result isolation — upsert, not append. Re-running one
# configuration must replace only its own rows, never duplicate or corrupt
# another configuration's.
# --------------------------------------------------------------------------
def upsert_rows(new_rows: list[dict], path: Path, fields: list[str], key_field: str) -> list[dict]:
    """Replace any existing rows sharing new_rows' key_field value; keep the rest."""
    existing: list[dict] = []
    if path.exists():
        existing = _read_rows(path)

    new_keys = {str(row[key_field]) for row in new_rows}
    kept = [row for row in existing if str(row.get(key_field)) not in new_keys]
    # Stringify uniformly. Without this, freshly-upserted rows keep their
    # native int/float types while rows read back from disk are all strings —
    # the SAME file would hand two different types for the same column
    # depending on whether a row was just added or reloaded.
    combined = kept + [{field: str(row.get(field, "")) for field in fields} for row in new_rows]
    combined.sort(key=lambda row: (int(row["chunk_size"]), int(row.get("k", 0))))

    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(combined)
    return combined


def upsert_config_rows(chunk_size: int, new_rows: list[dict]) -> list[dict]:
    tagged = [{**row, "chunk_size": chunk_size} for row in new_rows]
    return upsert_rows(tagged, CONFIGS_CSV, CONFIG_ROW_FIELDS, key_field="chunk_size")


def upsert_rank_rows(chunk_size: int, new_rows: list[dict]) -> list[dict]:
    """Ranks upsert by (chunk_size, question_id) — chunk_size alone would
    collapse all 25 questions into one key and delete the other 24."""
    existing: list[dict] = []
    if RANKS_CSV.exists():
        existing = _read_rows(RANKS_CSV)
    # Stringify uniformly — same reason as upsert_rows: a freshly-tagged row
    # must return the same types as one just read back off disk.
    tagged = [{field: str(row.get(field, "")) for field in RANK_ROW_FIELDS}
              for row in (dict(row, chunk_size=chunk_size) for row in new_rows)]

    new_keys = {(row["chunk_size"], row["question_id"]) for row in tagged}
    kept = [row for row in existing
            if (row["chunk_size"], row["question_id"]) not in new_keys]
    combined = kept + tagged
    combined.sort(key=lambda row: (int(row["chunk_size"]), row["question_id"]))

    RANKS_CSV.parent.mkdir(exist_ok=True)
    with RANKS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RANK_ROW_FIELDS)
        writer.writeheader()
        writer.writerows(combined)
    return combined


# --------------------------------------------------------------------------
# Pre-registered selection rule — applied mechanically, never re-derived
# after seeing which configuration "looks better".
# --------------------------------------------------------------------------
def select_winning_config(config_rows: list[dict], rank_rows: list[dict]) -> tuple[str, list[str]]:
    """Pick the Phase 7B configuration under the rule fixed before this ran:

        1. highest Gold Span Coverage @5
        2. highest Gold Span Any Recall @5
        3. lowest median First Gold Span Rank
        4. highest Gold Span Coverage @3
        5. fewer chunks / smaller index

    Document Recall is excluded on purpose — the frozen baseline already
    showed it saturated at 100%, so it cannot discriminate between configs.
    """
    at_k5 = {row["chunk_size"]: row for row in config_rows if int(row["k"]) == 5}
    at_k3 = {row["chunk_size"]: row for row in config_rows if int(row["k"]) == 3}

    medians: dict[str, float] = {}
    for size in at_k5:
        ranks = [int(r["first_rank"]) for r in rank_rows
                 if str(r["chunk_size"]) == str(size) and str(r["first_rank"]) != ""]
        medians[size] = statistics.median(ranks) if ranks else float("inf")

    def sort_key(size: str):
        row5, row3 = at_k5[size], at_k3[size]
        return (
            -float(row5["gold_span_coverage"]),
            -float(row5["gold_span_any_recall"]),
            medians[size],
            -float(row3["gold_span_coverage"]),
            int(row5["chunk_count"]),
        )

    ranking = sorted(at_k5, key=sort_key)
    return ranking[0], ranking
