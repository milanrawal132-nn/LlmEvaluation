"""Validate the LLM judge against human labels.

Run from the project root, after filling in results/human_review_template.csv:
    ./.venv/bin/python -u scripts/compare_judge_to_human.py

Until this has been run, every Phase 6 number is produced by an instrument
nobody has calibrated. The judge might be measuring what you think it is
measuring. It might not be. Agreement with a human is the only way to find out.

Agreement is reported PER METRIC, never pooled. A judge can be excellent at
relevance and useless at faithfulness, and one blended number would hide that.

Reported per metric:
    agreement       how often judge and human gave the same label
    judge-yes/human-no   the judge was too generous -> your scores are inflated
    judge-no/human-yes   the judge was too strict   -> your scores are deflated

The two error directions are NOT interchangeable. A generous judge tells you
the system is better than it is, which is the dangerous direction.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RESULTS_DIR = Path("results")
HUMAN_CSV = RESULTS_DIR / "human_review_template.csv"

# Newest verdicts by default. The pre-calibration run stays on disk and can be
# compared with --judge, so "did calibration help?" is always answerable.
RECALIBRATED_CSV = RESULTS_DIR / "phase6_generation_recalibrated.csv"
PRECALIBRATION_CSV = RESULTS_DIR / "phase6_generation_majority3.csv"

# judge column -> human column
METRIC_PAIRS = [
    ("correct", "human_correct"),
    ("faithful", "human_faithful"),
    ("relevant", "human_relevant"),
]


def parse_label(value: str, question_id: str, column: str) -> bool:
    """Read a human 1/0 label, refusing anything ambiguous.

    We do NOT silently treat a blank or a typo as 0. A missing label is a
    missing measurement, and quietly counting it as "no" would manufacture
    disagreement out of an unfinished sheet.
    """
    cleaned = value.strip().lower()
    if cleaned in {"1", "y", "yes", "true"}:
        return True
    if cleaned in {"0", "n", "no", "false"}:
        return False
    raise SystemExit(
        f"{question_id}: {column} is {value!r}. Fill every label with 1 or 0 "
        f"in {HUMAN_CSV} before running this."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judge", type=Path, default=None,
        help=f"verdicts to compare (default: {RECALIBRATED_CSV} if present, "
             f"else {PRECALIBRATION_CSV})",
    )
    args = parser.parse_args()

    judge_csv = args.judge or (
        RECALIBRATED_CSV if RECALIBRATED_CSV.exists() else PRECALIBRATION_CSV
    )
    for path in (judge_csv, HUMAN_CSV):
        if not path.exists():
            raise SystemExit(f"{path} not found.")
    print(f"judge verdicts: {judge_csv}")
    print(f"human labels  : {HUMAN_CSV}\n")

    judge = {r["question_id"]: r for r in csv.DictReader(judge_csv.open(encoding="utf-8"))}
    human_rows = list(csv.DictReader(HUMAN_CSV.open(encoding="utf-8")))

    unlabelled = [r["question_id"] for r in human_rows
                  if not any(r[c].strip() for c in ("human_correct", "human_faithful", "human_relevant"))]
    if len(unlabelled) == len(human_rows):
        raise SystemExit(
            f"{HUMAN_CSV} has no labels yet. Fill it in first — see "
            f"{RESULTS_DIR / 'human_review_context.md'}."
        )

    missing = [r["question_id"] for r in human_rows if r["question_id"] not in judge]
    if missing:
        raise SystemExit(f"no judge verdict for: {', '.join(missing)}")

    print(f"comparing {len(human_rows)} questions\n")
    print(f"{'metric':<14}{'agree':>9}{'judge=Y/human=N':>18}{'judge=N/human=Y':>18}")
    print("-" * 59)

    disagreements = []
    for judge_column, human_column in METRIC_PAIRS:
        agree = too_generous = too_strict = 0
        for row in human_rows:
            qid = row["question_id"]
            h = parse_label(row[human_column], qid, human_column)
            j = bool(int(judge[qid][judge_column]))
            if j == h:
                agree += 1
            elif j and not h:
                too_generous += 1
                disagreements.append((qid, judge_column, "judge=YES human=NO", row["notes"]))
            else:
                too_strict += 1
                disagreements.append((qid, judge_column, "judge=NO human=YES", row["notes"]))

        n = len(human_rows)
        print(f"{judge_column:<14}{agree / n:>8.0%}{too_generous:>18}{too_strict:>18}")

    if disagreements:
        print("\n" + "-" * 59)
        print("DISAGREEMENTS — read every one of these before trusting the metric")
        print("-" * 59)
        for qid, metric, direction, notes in disagreements:
            print(f"  {qid:<6}{metric:<11}{direction}")
            if notes.strip():
                print(f"         note: {notes.strip()}")
    else:
        print("\nno disagreements.")

    print(
        "\nReminder: agreement on 25 questions is a smoke test, not a "
        "calibration.\nA metric with low agreement should be fixed before any "
        "number using it is\nreported or compared across configurations."
    )


if __name__ == "__main__":
    main()
