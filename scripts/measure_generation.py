"""Phase 6: measure GENERATION, conditioned on what retrieval actually found.

Run from the project root:
    ./.venv/bin/python -u scripts/measure_generation.py

The whole design of this script is one idea: never report an accuracy number
without saying whether the evidence was in the context. "60% correct" means
completely different things depending on whether the model read the answer or
remembered it, and our corpus (Infosys, Reliance, Tata Motors annual reports)
is certainly in the model's training data.

So every question is scored on two axes at once:

                    evidence retrieved?
                     NO            YES
                +-------------+-------------+
    correct YES | UNSUPPORTED | GROUNDED    |
                | (memorised) | (real win)  |
                +-------------+-------------+
    correct NO  | RETRIEVAL   | GENERATION  |
                | failure     | failure     |
                +-------------+-------------+

Nothing here changes the pipeline. Retrieval, chunking and TOP_K are frozen at
the Phase 5 baseline.
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.evaluation import (  # noqa: E402
    DEFAULT_EVIDENCE_MODE,
    JUDGE_REPETITIONS,
    FAILURE_LABELS,
    Evidence,
    any_evidence_at_k,
    classify_failure,
    document_recall_at_k,
    evidence_coverage_at_k,
    is_abstention,
    judge_correctness,
    judge_faithfulness,
    judge_relevance,
)
from src.generation import generate  # noqa: E402
from src.retrieval import TOP_K, retrieve  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
STORE_DIR = Path("data/chroma")
RESULTS_DIR = Path("results")


def load_gold() -> tuple[list[dict], dict[str, list[Evidence]]]:
    questions = list(csv.DictReader(QUESTIONS_CSV.open(encoding="utf-8")))
    by_question: dict[str, list[Evidence]] = defaultdict(list)
    for row in csv.DictReader(EVIDENCE_CSV.open(encoding="utf-8")):
        by_question[row["question_id"]].append(
            Evidence(
                evidence_id=row["evidence_id"],
                question_id=row["question_id"],
                relevant_document=row["relevant_document"],
                relevant_pages=row["relevant_pages"],
                evidence_text=row["evidence_text"],
            )
        )
    return questions, by_question


def run_one(question: dict, evidence: list[Evidence], repetitions: int) -> dict:
    """Answer one question end to end and score it on every axis."""
    chunks = retrieve(question["question"], STORE_DIR, k=TOP_K)
    answer = generate(question["question"], chunks)

    mode = question.get("evidence_mode") or DEFAULT_EVIDENCE_MODE
    evidence_hit = any_evidence_at_k(chunks, evidence, TOP_K)
    abstained = is_abstention(answer.text)

    correct = judge_correctness(answer.text, question["reference_answer"], repetitions)
    faithful = judge_faithfulness(answer.text, chunks, repetitions)
    relevant = judge_relevance(answer.text, question["question"], repetitions)

    return {
        "question_id": question["question_id"],
        "difficulty": question["difficulty"],
        "question_type": question["question_type"],
        "document_hit": int(document_recall_at_k(chunks, evidence, TOP_K)),
        "evidence_hit": int(evidence_hit),
        "coverage": round(evidence_coverage_at_k(chunks, evidence, TOP_K, mode), 4),
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


def pct(rows: list[dict], key: str) -> str:
    """Percentage over a subset, printed as '-' when the subset is empty.

    Beginner trap this guards: a 0/0 group silently rendering as 0% looks like
    a total failure when it is actually no data at all.
    """
    if not rows:
        return "   -"
    return f"{sum(r[key] for r in rows) / len(rows):>4.0%}"


def report(rows: list[dict], repetitions: int) -> None:
    n = len(rows)

    print("\n" + "=" * 68)
    print(f"PHASE 6 GENERATION  (gpt-4o-mini, TOP_K={TOP_K}, retrieval frozen, "
          f"majority-of-{repetitions} judging)")
    print("=" * 68)
    print(f"{'Correctness':<22}{pct(rows, 'correct')}   answers matching the reference")
    print(f"{'Faithfulness':<22}{pct(rows, 'faithful')}   every claim backed by the context")
    print(f"{'Relevance':<22}{pct(rows, 'relevant')}   addressed the question asked")
    print(f"{'Abstention rate':<22}{pct(rows, 'abstained')}   said \"I don't know\"")

    # ---- the conditional breakdown: the number that actually means something
    with_ev = [r for r in rows if r["evidence_hit"]]
    without = [r for r in rows if not r["evidence_hit"]]

    print("\n" + "-" * 68)
    print("BY WHETHER THE EVIDENCE WAS ACTUALLY RETRIEVED")
    print("-" * 68)
    print(f"{'group':<26}{'n':>4}{'correct':>10}{'faithful':>10}{'abstained':>11}")
    print(f"{'evidence in context':<26}{len(with_ev):>4}"
          f"{pct(with_ev, 'correct'):>10}{pct(with_ev, 'faithful'):>10}{pct(with_ev, 'abstained'):>11}")
    print(f"{'evidence NOT in context':<26}{len(without):>4}"
          f"{pct(without, 'correct'):>10}{pct(without, 'faithful'):>10}{pct(without, 'abstained'):>11}")

    # ---- taxonomy
    print("\n" + "-" * 68)
    print("FAILURE TAXONOMY")
    print("-" * 68)
    counts = Counter(r["failure_label"] for r in rows)
    for label, description in FAILURE_LABELS.items():
        count = counts.get(label, 0)
        qids = ", ".join(r["question_id"] for r in rows if r["failure_label"] == label)
        print(f"{label:<32}{count:>3} ({count / n:>4.0%})  {description}")
        if qids:
            print(f"{'':<32}     {qids}")

    # ---- the split the taxonomy exists to produce
    retrieval_bugs = counts["retrieval_failure_honest"] + counts["retrieval_failure_hallucinated"]
    generation_bugs = counts["generation_failure"] + counts["generation_refusal"]
    print("\n" + "-" * 68)
    print(f"retrieval's fault : {retrieval_bugs:>3} / {n}")
    print(f"generation's fault: {generation_bugs:>3} / {n}")
    unsupported = counts["unsupported_correct"]
    print(f"needs human review: {unsupported:>3} / {n}  (correct without evidence)")
    if unsupported == 0:
        # Deliberate phrasing. Zero observations in a 25-question pilot at one
        # value of K is NOT proof that the model never answers from memory.
        print(f"  -> no unsupported-correct answers were OBSERVED in this "
              f"{n}-question pilot at K={TOP_K}.")
        print("     This is not proof of no training-data contamination.")

    print("\n" + "-" * 68)
    print("BY DIFFICULTY")
    print("-" * 68)
    print(f"{'group':<26}{'n':>4}{'correct':>10}{'faithful':>10}{'abstained':>11}")
    for level in ("easy", "medium", "difficult"):
        group = [r for r in rows if r["difficulty"] == level]
        print(f"{level:<26}{len(group):>4}"
              f"{pct(group, 'correct'):>10}{pct(group, 'faithful'):>10}{pct(group, 'abstained'):>11}")

    total_cost = sum(r["cost_usd"] for r in rows)
    mean_latency = sum(r["latency_seconds"] for r in rows) / n
    print(f"\nanswering cost: ${total_cost:.4f} for {n} questions "
          f"(${total_cost / n:.5f} each), mean latency {mean_latency:.2f}s")
    print("(judge calls are evaluation overhead and are not counted above)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repetitions", type=int, default=JUDGE_REPETITIONS,
        help="judge calls per verdict; majority wins. 1 reproduces the "
             "single-run diagnostics (default: %(default)s)",
    )
    parser.add_argument(
        "--out", default=None,
        help="output CSV name under results/ (default: derived from --repetitions)",
    )
    args = parser.parse_args()

    # Separate default filenames so a majority-of-3 run can never silently
    # overwrite the single-run diagnostics, or the reverse.
    name = args.out or (
        "phase6_generation_baseline.csv" if args.repetitions == 1
        else f"phase6_generation_majority{args.repetitions}.csv"
    )

    questions, evidence_by_question = load_gold()
    print(f"scoring {len(questions)} questions at TOP_K={TOP_K}, "
          f"majority-of-{args.repetitions} judging\n")

    rows = []
    for i, question in enumerate(questions, start=1):
        row = run_one(question, evidence_by_question[question["question_id"]], args.repetitions)
        rows.append(row)
        print(f"  [{i:>2}/{len(questions)}] {row['question_id']}  "
              f"ev={row['evidence_hit']} correct={row['correct']} "
              f"faith={row['faithful']} abst={row['abstained']}  {row['failure_label']}")

    report(rows, args.repetitions)

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / name
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nper-question rows (including every answer) written to {out}")


if __name__ == "__main__":
    main()
