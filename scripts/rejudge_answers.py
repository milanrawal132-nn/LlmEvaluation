"""Re-score EXISTING answers with the current judge rubrics. No generation.

Run from the project root:
    ./.venv/bin/python -u scripts/rejudge_answers.py

Why this exists as a separate script: the generator is non-deterministic, so
re-running scripts/measure_generation.py would produce different answers and
the judge change would be confounded with generation drift. Here the answers
are FIXED — read from a previous run — and only the verdicts are recomputed.
That is the only way to attribute a change to the rubric.

It writes a NEW file rather than editing the source, so the pre-calibration
verdicts stay on disk as evidence of what changed.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.evaluation import (  # noqa: E402
    JUDGE_REPETITIONS,
    classify_failure,
    is_abstention,
    judge_correctness,
    judge_faithfulness,
    judge_relevance,
)
from src.retrieval import TOP_K, retrieve  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
STORE_DIR = Path("data/chroma")
RESULTS_DIR = Path("results")

DEFAULT_SOURCE = RESULTS_DIR / "phase6_generation_majority3.csv"
DEFAULT_OUT = RESULTS_DIR / "phase6_generation_recalibrated.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="run whose ANSWERS are reused (default: %(default)s)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="where to write new verdicts (default: %(default)s)")
    parser.add_argument("--repetitions", type=int, default=JUDGE_REPETITIONS)
    args = parser.parse_args()

    if args.out.resolve() == args.source.resolve():
        raise SystemExit("refusing to overwrite the source run — choose another --out")

    questions = {r["question_id"]: r
                 for r in csv.DictReader(QUESTIONS_CSV.open(encoding="utf-8"))}
    rows = list(csv.DictReader(args.source.open(encoding="utf-8")))
    print(f"re-judging {len(rows)} FIXED answers from {args.source}")
    print(f"majority-of-{args.repetitions}, TOP_K={TOP_K}\n")

    out_rows, changes = [], []
    for index, row in enumerate(rows, start=1):
        qid = row["question_id"]
        question = questions[qid]
        answer = row["answer"]

        # Retrieval is deterministic given the index, so this reproduces the
        # exact context the answer was generated from.
        chunks = retrieve(question["question"], STORE_DIR, k=TOP_K)

        abstained = is_abstention(answer)
        correct = judge_correctness(answer, question["reference_answer"], args.repetitions)
        faithful = judge_faithfulness(answer, chunks, args.repetitions)
        relevant = judge_relevance(answer, question["question"], args.repetitions)

        new = dict(row)
        new.update({
            "abstained": int(abstained),
            "correct": int(correct),
            "faithful": int(faithful),
            "relevant": int(relevant),
            "failure_label": classify_failure(bool(int(row["evidence_hit"])), correct, abstained),
        })
        out_rows.append(new)

        moved = [f"{key}: {row[key]}->{new[key]}"
                 for key in ("correct", "faithful", "relevant")
                 if str(row[key]) != str(new[key])]
        if moved:
            changes.append(f"  {qid}: " + "; ".join(moved))
        print(f"  [{index:>2}/{len(rows)}] {qid}  correct={new['correct']} "
              f"faith={new['faithful']} rel={new['relevant']}"
              f"{'   <- moved' if moved else ''}")

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\n{len(changes)} verdicts moved:")
    for line in changes:
        print(line)

    # Sanity: the answers must be untouched, or the comparison is invalid.
    assert [r["answer"] for r in rows] == [r["answer"] for r in out_rows]
    print(f"\nanswers unchanged (verified) -> {args.out}")


if __name__ == "__main__":
    main()
