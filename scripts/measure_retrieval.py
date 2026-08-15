"""Phase 5: measure RETRIEVAL ONLY, against the untouched baseline.

No generation, no LLM judging, no tuning. This script answers one question:
when we ask our 25 gold questions, does the librarian bring back the pages
that actually contain the answers?

Run from the project root:
    ./.venv/bin/python -u scripts/measure_retrieval.py

Order matters here. The ruler is checked BEFORE anything is measured with it:
if a gold snippet sits in no single chunk in the index, its question can never
score full coverage, and that chunking artefact would read as a retrieval
failure. So unfindable_evidence() runs first and the script refuses to report
metrics if it finds anything.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

# Python puts the SCRIPT's folder on sys.path, not the folder you ran it from,
# so `import src...` fails without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.evaluation import (  # noqa: E402  (needs the key loaded first)
    DEFAULT_EVIDENCE_MODE,
    Evidence,
    any_evidence_at_k,
    document_recall_at_k,
    evidence_coverage_at_k,
    unfindable_evidence,
)
from src.ingestion import COLLECTION_NAME  # noqa: E402
from src.retrieval import retrieve  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
STORE_DIR = Path("data/chroma")
RESULTS_DIR = Path("results")

# The cut-offs we report. We retrieve MAX_K once per question and slice it,
# rather than querying four times — the top 3 of a top-10 query is exactly the
# top 3 of a top-3 query, so four queries would cost 4x for identical numbers.
K_VALUES = (1, 3, 5, 10)
MAX_K = max(K_VALUES)


def load_gold() -> tuple[list[dict], dict[str, list[Evidence]]]:
    """Read the gold set: questions, and their evidence grouped by question."""
    questions = list(csv.DictReader(QUESTIONS_CSV.open(encoding="utf-8")))

    evidence_by_question: dict[str, list[Evidence]] = defaultdict(list)
    for row in csv.DictReader(EVIDENCE_CSV.open(encoding="utf-8")):
        evidence_by_question[row["question_id"]].append(
            Evidence(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                relevant_document=row["relevant_document"],
                relevant_pages=row["relevant_pages"],
                evidence_text=row["evidence_text"],
            )
        )
    return questions, evidence_by_question


def all_indexed_chunk_texts() -> list[str]:
    """Every chunk currently in the index, for the ruler-quality check.

    Read directly from Chroma rather than re-chunking the PDFs, because what
    matters is what is actually searchable — not what we believe we indexed.
    """
    client = chromadb.PersistentClient(path=str(STORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    return collection.get(include=["documents"])["documents"]


def check_ruler(evidence_by_question: dict[str, list[Evidence]]) -> None:
    """Refuse to measure if any gold snippet is unreachable in principle.

    A snippet longer than CHUNK_OVERLAP can straddle a chunk boundary and sit
    wholly inside no chunk. Retrieval could then be perfect and coverage would
    still never reach 1.0. That is a fact about the ruler, not the pipeline.
    """
    chunk_texts = all_indexed_chunk_texts()
    print(f"index contains {len(chunk_texts):,} chunks")

    flat = [item for items in evidence_by_question.values() for item in items]
    missing = unfindable_evidence(flat, chunk_texts)

    if missing:
        by_id = {item.evidence_id: item for item in flat}
        print(f"\nRULER CHECK FAILED — {len(missing)} of {len(flat)} snippets are unfindable:")
        for evidence_id in missing:
            item = by_id[evidence_id]
            print(f"  {evidence_id} (q={item.question_id}) {item.relevant_document} "
                  f"p.{item.relevant_pages}: {item.evidence_text[:90]}...")
        raise SystemExit(
            "\nCoverage numbers would be capped below 1.0 by chunking, not by "
            "retrieval. Fix the gold set or the chunk parameters before measuring."
        )

    print(f"ruler check PASSED — all {len(flat)} gold snippets sit inside a chunk\n")


def score_all(questions: list[dict], evidence_by_question: dict[str, list[Evidence]]) -> list[dict]:
    """Retrieve once per question and score it at every K."""
    rows: list[dict] = []
    for i, question in enumerate(questions, start=1):
        qid = question["question_id"]
        evidence = evidence_by_question[qid]
        mode = question.get("evidence_mode") or DEFAULT_EVIDENCE_MODE

        retrieved = retrieve(question["question"], STORE_DIR, k=MAX_K)

        row = {
            "question_id": qid,
            "difficulty": question["difficulty"],
            "question_type": question["question_type"],
            "evidence_mode": mode,
            "n_evidence": len(evidence),
            "gold_documents": "|".join(sorted({e.relevant_document for e in evidence})),
            "top1_document": retrieved[0].source_document if retrieved else "",
            "top1_score": round(retrieved[0].score, 4) if retrieved else 0.0,
        }
        for k in K_VALUES:
            row[f"doc_recall@{k}"] = int(document_recall_at_k(retrieved, evidence, k))
            row[f"any_evidence@{k}"] = int(any_evidence_at_k(retrieved, evidence, k))
            row[f"coverage@{k}"] = round(evidence_coverage_at_k(retrieved, evidence, k, mode), 4)
        rows.append(row)

        print(f"  [{i:>2}/{len(questions)}] {qid}  doc@5={row['doc_recall@5']}  "
              f"any@5={row['any_evidence@5']}  cov@5={row['coverage@5']:.2f}")
    return rows


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def print_headline(rows: list[dict]) -> None:
    print("\n" + "=" * 62)
    print("BASELINE RETRIEVAL  (chunk=500/50, text-embedding-3-small, untuned)")
    print("=" * 62)
    print(f"{'metric':<24}" + "".join(f"{'@' + str(k):>9}" for k in K_VALUES))
    print("-" * 62)
    for label, key in [
        ("Document Recall", "doc_recall"),
        ("Any Evidence Recall", "any_evidence"),
        ("Evidence Coverage", "coverage"),
    ]:
        cells = "".join(f"{mean([r[f'{key}@{k}'] for r in rows]):>8.1%} " for k in K_VALUES)
        print(f"{label:<24}{cells}")


def print_breakdown(rows: list[dict], field: str, title: str, order: list[str] | None = None) -> None:
    """Group rows by one field and report the three metrics at K=5.

    K=5 because that is TOP_K — the number of chunks the generator will
    actually see in Phase 6. The breakdowns exist to locate WHERE retrieval
    fails, so they are reported at the K we ship.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)

    keys = [k for k in (order or []) if k in groups] + sorted(set(groups) - set(order or []))

    print("\n" + "-" * 72)
    print(f"{title} (at K=5)")
    print("-" * 72)
    print(f"{'group':<34}{'n':>4}{'doc':>10}{'any':>10}{'coverage':>12}")
    for key in keys:
        group = groups[key]
        print(
            f"{key:<34}{len(group):>4}"
            f"{mean([r['doc_recall@5'] for r in group]):>9.0%} "
            f"{mean([r['any_evidence@5'] for r in group]):>9.0%} "
            f"{mean([r['coverage@5'] for r in group]):>11.0%}"
        )


def main() -> None:
    questions, evidence_by_question = load_gold()
    print(f"gold set: {len(questions)} questions, "
          f"{sum(len(v) for v in evidence_by_question.values())} evidence passages\n")

    check_ruler(evidence_by_question)

    rows = score_all(questions, evidence_by_question)

    print_headline(rows)
    print_breakdown(rows, "difficulty", "BY DIFFICULTY", order=["easy", "medium", "difficult"])
    print_breakdown(rows, "gold_documents", "BY GOLD DOCUMENT")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "phase5_retrieval_baseline.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nper-question rows written to {out}")


if __name__ == "__main__":
    main()
