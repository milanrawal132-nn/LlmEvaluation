"""Pre-Phase-7A reproducibility gate: does the rebuilt 500/50 index reproduce
the frozen Phase 5 baseline?

Run from the project root, AFTER rebuilding the index with scripts/build_index.py:
    ./.venv/bin/python -u scripts/verify_reproducibility.py

This is a gate, not a measurement. Phase 7A compares chunk sizes against this
index; if the rebuild silently changed anything, every 7A number would be
compared against a moving baseline without anyone knowing it moved.

IMPORTANT CONFOUND, isolated deliberately:
evidence.csv grew from 31 to 35 rows between the frozen Phase 5 run and today
(the evidence-groups refinement added page-43 alternates for q010). The old
TEXT-based metric is ungrouped — it divides matched rows by ALL rows for a
question — so re-running it against the CURRENT evidence.csv would change
q010's denominator and could look like a retrieval regression that is
actually a gold-set change.

To keep the gate honest, this script computes the old metric TWICE:
  - against a snapshot of evidence.csv taken BEFORE the groups refinement
    (the actual input the frozen baseline was measured against) — this is
    the number that must reproduce exactly, and it is the gate criterion.
  - against the CURRENT evidence.csv — reported for transparency, expected
    to differ on q010, and explicitly NOT part of the pass/fail decision.
"""

import csv
import hashlib
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.evaluation import (  # noqa: E402
    DEFAULT_EVIDENCE_MODE,
    Evidence,
    any_evidence_at_k,
    document_recall_at_k,
    evidence_coverage_at_k,
)
from src.ingestion import COLLECTION_NAME  # noqa: E402
from src.retrieval import retrieve  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
# The 31-row snapshot taken immediately before the evidence-groups refinement
# — the actual gold set the FROZEN artefacts were measured against.
PRE_GROUPS_EVIDENCE_CSV = Path(
    "/private/tmp/claude-501/-Users-shubhamrawal-Desktop-Milan-Rawal-LlmEvaluation/"
    "79044a34-3f84-46de-a1f7-68400945895e/scratchpad/evidence.pre-groups.csv"
)
STORE_DIR = Path("data/chroma")

FROZEN_CSV = Path("results/phase5_retrieval_baseline.FROZEN.csv")
FROZEN_MD = Path("results/phase5_retrieval_baseline.FROZEN.md")

K_VALUES = (1, 3, 5, 10)
MAX_K = max(K_VALUES)

# Files this gate must prove are untouched, with their known-good hashes.
# Sourced from the last verified check, not recomputed here — if this script
# computed its own "expected" hash it could never catch a silent edit.
FROZEN_HASHES = {
    "results/phase5_retrieval_baseline.FROZEN.csv": "afa17df00bcd44fb",
    "results/phase5_retrieval_baseline.FROZEN.md": "cdd96c180c39b4c0",
    "results/phase6_generation_baseline.csv": "2f161effc81aad50",
    "results/phase6_generation_majority3.csv": "d2cb81a32f4b5693",
}


def load_evidence(path: Path) -> dict[str, list[Evidence]]:
    """Read a gold-evidence CSV, tolerant of stray leading/trailing blank lines.

    We do NOT rewrite the source file to strip these — this gate must not
    alter evidence.csv, so a blank line ahead of the header (however it got
    there) is worked around at read time rather than "cleaned up" on disk.
    """
    lines = [line for line in path.open(encoding="utf-8") if line.strip()]
    by_question: dict[str, list[Evidence]] = defaultdict(list)
    for row in csv.DictReader(lines):
        by_question[row["question_id"]].append(
            Evidence(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                relevant_document=row["relevant_document"],
                relevant_pages=row["relevant_pages"],
                evidence_text=row["evidence_text"],
            )
        )
    return by_question


def score(questions: list[dict], evidence_by_question: dict[str, list[Evidence]]) -> dict[int, dict]:
    """Retrieve once per question at MAX_K, score every K by slicing."""
    totals = {k: {"doc": 0, "any": 0, "cov": 0.0} for k in K_VALUES}
    n = len(questions)

    for question in questions:
        qid = question["question_id"]
        evidence = evidence_by_question[qid]
        mode = question.get("evidence_mode") or DEFAULT_EVIDENCE_MODE
        retrieved = retrieve(question["question"], STORE_DIR, k=MAX_K)

        for k in K_VALUES:
            totals[k]["doc"] += int(document_recall_at_k(retrieved, evidence, k))
            totals[k]["any"] += int(any_evidence_at_k(retrieved, evidence, k))
            totals[k]["cov"] += evidence_coverage_at_k(retrieved, evidence, k, mode)

    return {
        k: {
            "doc_recall": totals[k]["doc"] / n,
            "any_evidence": totals[k]["any"] / n,
            "coverage": totals[k]["cov"] / n,
        }
        for k in K_VALUES
    }


def check_index_metadata() -> int:
    """Confirm the rebuilt index carries offsets alongside existing provenance."""
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    count = collection.count()
    sample = collection.get(limit=5, include=["metadatas"])

    required = {"source_document", "chunk_index", "pages", "start_char", "end_char"}
    print(f"chunk count: {count:,}")
    for meta in sample["metadatas"]:
        missing = required - set(meta)
        if missing:
            raise SystemExit(f"metadata missing {missing} on a sampled chunk: {meta}")
    example = sample["metadatas"][0]
    print(f"sample metadata: {example}")
    print("all required fields present: source_document, chunk_index, pages, "
          "start_char, end_char\n")
    return count


def parse_frozen_table() -> dict[int, dict[str, float]]:
    """Read the @1/@3/@5/@10 table out of the frozen CSV (ground truth)."""
    rows = list(csv.DictReader(FROZEN_CSV.open(encoding="utf-8")))
    n = len(rows)
    out = {}
    for k in K_VALUES:
        out[k] = {
            "doc_recall": sum(int(r[f"doc_recall@{k}"]) for r in rows) / n,
            "any_evidence": sum(int(r[f"any_evidence@{k}"]) for r in rows) / n,
            "coverage": sum(float(r[f"coverage@{k}"]) for r in rows) / n,
        }
    return out


def verify_hashes() -> bool:
    print("frozen artefact hashes:")
    all_ok = True
    for path_str, expected in FROZEN_HASHES.items():
        path = Path(path_str)
        if not path.exists():
            print(f"  MISSING  {path_str}")
            all_ok = False
            continue
        got = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        ok = got == expected
        all_ok &= ok
        print(f"  {'OK ' if ok else 'CHANGED'}  {path_str}  {got}")
    return all_ok


def report_disk() -> None:
    usage = shutil.disk_usage("/")
    free_gib = usage.free / (1024**3)
    print(f"disk free: {free_gib:.1f} GiB")


def main() -> None:
    print("=" * 66)
    print("PRE-PHASE-7A REPRODUCIBILITY GATE")
    print("=" * 66)

    chunk_count = check_index_metadata()

    questions = list(csv.DictReader(QUESTIONS_CSV.open(encoding="utf-8")))

    frozen = parse_frozen_table()

    if not PRE_GROUPS_EVIDENCE_CSV.exists():
        raise SystemExit(
            f"pre-groups evidence snapshot not found at {PRE_GROUPS_EVIDENCE_CSV} "
            "— cannot isolate the gold-set confound. Aborting rather than "
            "reporting a comparison that mixes two variables."
        )
    gate_evidence = load_evidence(PRE_GROUPS_EVIDENCE_CSV)
    gate_result = score(questions, gate_evidence)

    print("-" * 66)
    print("GATE CHECK — rebuilt index, evidence.csv snapshot matching FROZEN input")
    print("-" * 66)
    print(f"{'':>4}{'Document Recall':>18}{'Any Evidence':>16}{'Coverage':>12}")
    print(f"{'K':>4}{'now':>9}{'frozen':>9}{'now':>8}{'frozen':>8}{'now':>7}{'frozen':>7}")

    mismatches = []
    for k in K_VALUES:
        now, base = gate_result[k], frozen[k]
        row = f"{k:>4}"
        for metric in ("doc_recall", "any_evidence", "coverage"):
            diff = abs(now[metric] - base[metric])
            # Floating rounding only — anything above this is a real drift,
            # not formatting noise.
            if diff > 0.0005:
                mismatches.append((k, metric, now[metric], base[metric]))
            row += f"{now[metric]:>8.1%}" if metric != "coverage" else f"{now[metric]:>7.1%}"
            row += f"{base[metric]:>8.1%}" if metric != "coverage" else f"{base[metric]:>7.1%}"
        print(row)

    print()
    if mismatches:
        print("MISMATCHES (beyond rounding):")
        for k, metric, now_val, base_val in mismatches:
            print(f"  K={k} {metric}: now={now_val:.4f} frozen={base_val:.4f}")
    else:
        print("no mismatches beyond floating-point rounding.")

    # Transparency run — current (post-groups) evidence.csv. NOT part of the
    # pass/fail decision; q010 is expected to move because its denominator
    # doubled when the p.43 alternates were added.
    current_evidence = load_evidence(EVIDENCE_CSV)
    current_result = score(questions, current_evidence)
    print("\n" + "-" * 66)
    print("TRANSPARENCY ONLY — same index, CURRENT evidence.csv (post-groups, "
          "35 rows). Not a gate criterion; q010's denominator changed.")
    print("-" * 66)
    print(f"{'K':>4}{'doc_recall':>12}{'any_evidence':>14}{'coverage':>10}")
    for k in K_VALUES:
        r = current_result[k]
        print(f"{k:>4}{r['doc_recall']:>11.1%}{r['any_evidence']:>13.1%}{r['coverage']:>9.1%}")

    hashes_ok = verify_hashes()
    print()
    report_disk()

    print("\n" + "=" * 66)
    passed = not mismatches and hashes_ok
    print(f"GATE RESULT: {'PASSED' if passed else 'FAILED — DO NOT START PHASE 7A'}")
    print("=" * 66)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
