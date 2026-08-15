"""Shared logic for Phase 7B: end-to-end robustness of the Phase 7A winner
against the frozen 500/50 baseline.

Three independent generation runs per configuration — not three judge votes
on one answer, three separate calls to generate() — because Phase 6 proved
the GENERATOR is non-deterministic (9 of 25 answers changed wording between
two runs, and one full taxonomy label flipped). A single run cannot tell a
real configuration difference from ordinary generation noise; only the
spread across repeated runs can.

Evidence-hit for the failure taxonomy uses the GROUP-AWARE gold-span metric
(gold_span_any_recall_at_k), not the legacy ungrouped ruler Phase 6 used.
This is a continuation of the direction Phase 7A already established — spans
and groups are the current primary ruler — applied consistently to BOTH
configurations, so the comparison stays apples-to-apples either way. It is
not a judge change: judge_correctness/faithfulness/relevance are frozen,
per "judge calibration is closed."
"""

import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from src.evaluation import (
    DEFAULT_EVIDENCE_MODE,
    classify_failure,
    gold_span_any_recall_at_k,
    is_abstention,
    judge_correctness,
    judge_faithfulness,
    judge_relevance,
)
from src.generation import generate
from src.retrieval import RetrievedChunk

import scripts.phase7a_lib as phase7a_lib

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
RESULTS_DIR = Path("results")
RAW_CSV = RESULTS_DIR / "phase7b_generation_runs.csv"
SUMMARY_MD = RESULTS_DIR / "phase7b_summary.md"

TOP_K = 5  # fixed for Phase 7B, per the pre-registered selection rule's own premise
DEFAULT_RUNS = 3

RAW_FIELDS = [
    "chunk_size", "run_index", "question_id", "difficulty", "question_type",
    "evidence_mode", "evidence_hit", "abstained", "correct", "faithful",
    "relevant", "failure_label", "input_tokens", "output_tokens",
    "cost_usd", "latency_seconds", "answer",
]


def load_questions() -> list[dict]:
    return phase7a_lib._read_rows(QUESTIONS_CSV)


def build_gold_spans() -> dict[str, list]:
    return phase7a_lib.build_gold_spans()


def run_one(question: dict, spans, retrieve_fn) -> dict:
    """One fresh generation + judgement for one question."""
    mode = question.get("evidence_mode") or DEFAULT_EVIDENCE_MODE
    chunks: list[RetrievedChunk] = retrieve_fn(question["question"], TOP_K)
    answer = generate(question["question"], chunks)

    evidence_hit = gold_span_any_recall_at_k(chunks, spans, TOP_K)
    abstained = is_abstention(answer.text)
    correct = judge_correctness(answer.text, question["reference_answer"])
    faithful = judge_faithfulness(answer.text, chunks)
    relevant = judge_relevance(answer.text, question["question"])

    return {
        "question_id": question["question_id"],
        "difficulty": question["difficulty"],
        "question_type": question["question_type"],
        "evidence_mode": mode,
        "evidence_hit": int(evidence_hit),
        "abstained": int(abstained),
        "correct": int(correct),
        "faithful": int(faithful),
        "relevant": int(relevant),
        "failure_label": classify_failure(evidence_hit, correct, abstained),
        "input_tokens": answer.input_tokens,
        "output_tokens": answer.output_tokens,
        "cost_usd": round(answer.cost_usd(), 6),
        "latency_seconds": round(answer.latency_seconds, 2),
        "answer": answer.text,
    }


def run_rate(rows: list[dict], field: str) -> float:
    return sum(row[field] for row in rows) / len(rows) if rows else 0.0


def summarize_run(rows: list[dict]) -> dict:
    return {
        "n": len(rows),
        "correct_rate": run_rate(rows, "correct"),
        "faithful_rate": run_rate(rows, "faithful"),
        "relevant_rate": run_rate(rows, "relevant"),
        "abstain_rate": run_rate(rows, "abstained"),
        "taxonomy": dict(Counter(row["failure_label"] for row in rows)),
    }


def spread(values: list[float]) -> dict:
    """mean/min/max/range across repeated runs — the noise this experiment exists to expose."""
    return {
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "range": max(values) - min(values),
    }


def config_spread(run_summaries: list[dict]) -> dict:
    return {
        metric: spread([run[metric] for run in run_summaries])
        for metric in ("correct_rate", "faithful_rate", "relevant_rate", "abstain_rate")
    }


def ranges_overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> bool:
    """Do two configs' observed ranges overlap?

    Not a significance test (explicitly out of scope for this project) — a
    plain, auditable check: if the ranges DON'T overlap, the difference
    survived the run-to-run noise we actually measured. If they DO overlap,
    three runs cannot rule out that the "difference" is noise.
    """
    return a_min <= b_max and b_min <= a_max


def upsert_raw_rows(chunk_size: int, new_rows: list[dict]) -> list[dict]:
    """Replace this config's rows only — re-running one config must not
    disturb or duplicate the other's."""
    existing: list[dict] = []
    if RAW_CSV.exists():
        existing = phase7a_lib._read_rows(RAW_CSV)

    tagged = [{field: str(row.get(field, "")) for field in RAW_FIELDS}
              for row in (dict(row, chunk_size=chunk_size) for row in new_rows)]

    kept = [row for row in existing if row["chunk_size"] != str(chunk_size)]
    combined = kept + tagged
    combined.sort(key=lambda row: (int(row["chunk_size"]), int(row["run_index"]), row["question_id"]))

    RESULTS_DIR.mkdir(exist_ok=True)
    with RAW_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RAW_FIELDS)
        writer.writeheader()
        writer.writerows(combined)
    return combined


def rows_for_config(all_rows: list[dict], chunk_size: int) -> list[dict]:
    return [row for row in all_rows if row["chunk_size"] == str(chunk_size)]


def rows_by_run(config_rows: list[dict]) -> dict[int, list[dict]]:
    by_run: dict[int, list[dict]] = defaultdict(list)
    for row in config_rows:
        by_run[int(row["run_index"])].append(
            {**row, "correct": int(row["correct"]), "faithful": int(row["faithful"]),
             "relevant": int(row["relevant"]), "abstained": int(row["abstained"])}
        )
    return dict(by_run)
