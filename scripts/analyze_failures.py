"""Phase 8: failure analysis — WHERE failures cluster, not just how many.

Run from the project root, using ALREADY-COMPUTED Phase 7B data
(chunk_size=600, the accepted configuration) — no new index, no API calls:

    ./.venv/bin/python -u scripts/analyze_failures.py

The Phase 6/7B taxonomy answers "how many of each failure type." This
answers a different question: "which SLICE of the question set is driving
them" — because that is what tells you what to fix next. A generation
failure concentrated in 'comparison' questions calls for a prompt fix; a
retrieval failure concentrated in one document calls for a chunking or
embedding fix. The same aggregate count can hide either cause, and averaging
across the whole set is exactly what erases the difference.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.phase7a_lib as phase7a_lib  # noqa: E402
import scripts.phase7b_lib as phase7b_lib  # noqa: E402
from src.evaluation import FAILURE_LABELS  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
RESULTS_DIR = Path("results")
OUT_CSV = RESULTS_DIR / "phase8_failure_breakdown.csv"
OUT_MD = RESULTS_DIR / "phase8_failure_analysis.md"

CHUNK_SIZE = 600  # the accepted configuration — Phase 7B's winner

# Below this many DISTINCT QUESTIONS, a group's percentages are reported but
# visually flagged: with 3 or fewer questions, one answer changing between
# runs swings the group's rate by 30+ points. That's not a finding, it's
# sample-size noise wearing a percentage sign.
SMALL_SAMPLE_QUESTIONS = 4


def question_to_document(evidence_rows: list[dict]) -> dict[str, str]:
    """Map each question to the (first alphabetically, if >1) document its
    gold evidence lives in — for the by-document breakdown."""
    by_question: dict[str, set[str]] = defaultdict(set)
    for row in evidence_rows:
        by_question[row["question_id"]].add(row["relevant_document"])
    return {
        qid: sorted(docs)[0].replace("_2025_26_annual_report.pdf", "")
                            .replace("_2024_25_annual_report.pdf", "")
        for qid, docs in by_question.items()
    }


def load_600_rows() -> list[dict]:
    all_rows = phase7a_lib._read_rows(phase7b_lib.RAW_CSV)
    rows = phase7b_lib.rows_for_config(all_rows, CHUNK_SIZE)
    if not rows:
        raise SystemExit(
            f"no Phase 7B rows for chunk_size={CHUNK_SIZE} in {phase7b_lib.RAW_CSV} — "
            f"run scripts/measure_phase7b.py first"
        )
    return rows


def breakdown_by(rows: list[dict], key_fn) -> dict[str, dict]:
    """Group rows by key_fn, then compute a taxonomy distribution per group.

    Returns {group_name: {"n_observations": int, "n_questions": int,
                           "counts": Counter, "rates": {label: float}}}
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)

    result = {}
    for name, group_rows in groups.items():
        n = len(group_rows)
        counts = Counter(row["failure_label"] for row in group_rows)
        result[name] = {
            "n_observations": n,
            "n_questions": len({row["question_id"] for row in group_rows}),
            "counts": counts,
            "rates": {label: counts.get(label, 0) / n for label in FAILURE_LABELS},
        }
    return result


def overall_rates(rows: list[dict]) -> dict[str, float]:
    n = len(rows)
    counts = Counter(row["failure_label"] for row in rows)
    return {label: counts.get(label, 0) / n for label in FAILURE_LABELS}


def lift(group_rate: float, overall_rate: float) -> float | None:
    """How over/under-represented a failure type is in this group vs the
    whole set. 1.0 = exactly average; 2.0 = twice as common in this group.
    None when the overall rate is 0 — lift is undefined, not infinite.
    """
    if overall_rate == 0:
        return None
    return group_rate / overall_rate


def print_breakdown(title: str, breakdown: dict[str, dict], baseline: dict[str, float]) -> None:
    print(f"\n{'-' * 78}\n{title}\n{'-' * 78}")
    print(f"{'group':<16}{'n_q':>5}{'n_obs':>7}   worst failure type (lift vs overall)")
    for name in sorted(breakdown, key=lambda g: breakdown[g]["n_questions"], reverse=True):
        stats = breakdown[name]
        flag = " *SMALL SAMPLE*" if stats["n_questions"] <= SMALL_SAMPLE_QUESTIONS else ""
        # The failure type most OVER-represented in this group relative to
        # the whole set — the thing worth investigating, not just the
        # largest raw count (which is usually just the most common label).
        lifts = {
            label: lift(rate, baseline[label])
            for label, rate in stats["rates"].items()
            if rate > 0
        }
        worst = max(lifts, key=lambda label: lifts[label] or 0) if lifts else None
        worst_desc = (
            f"{worst} ({stats['rates'][worst]:.0%}, {lifts[worst]:.1f}x overall)"
            if worst else "—"
        )
        print(f"{name:<16}{stats['n_questions']:>5}{stats['n_observations']:>7}   {worst_desc}{flag}")


def write_artifacts(
    rows: list[dict],
    by_type: dict, by_difficulty: dict, by_document: dict,
    baseline: dict[str, float],
) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_rows = []
    for dimension, breakdown in (
        ("question_type", by_type), ("difficulty", by_difficulty), ("document", by_document)
    ):
        for group, stats in breakdown.items():
            for label in FAILURE_LABELS:
                csv_rows.append({
                    "dimension": dimension,
                    "group": group,
                    "n_questions": stats["n_questions"],
                    "n_observations": stats["n_observations"],
                    "failure_label": label,
                    "count": stats["counts"].get(label, 0),
                    "rate": round(stats["rates"][label], 4),
                    "lift_vs_overall": (
                        round(l, 2) if (l := lift(stats["rates"][label], baseline[label])) is not None else ""
                    ),
                })
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\nsaved -> {OUT_CSV}")

    lines = [
        f"# Phase 8 — failure analysis (chunk_size={CHUNK_SIZE})\n",
        f"{len(rows)} observations: 3 independent generation runs x 25 questions, "
        f"using the Phase 7B-accepted configuration.\n",
        f"Groups with {SMALL_SAMPLE_QUESTIONS} or fewer distinct questions are "
        f"flagged SMALL SAMPLE — one answer changing between runs swings their "
        f"rate by 30+ points, so treat those rows as leads to check, not findings.\n",
        "## Overall taxonomy\n",
        "| label | count | rate |", "|---|---|---|",
    ]
    counts = Counter(row["failure_label"] for row in rows)
    for label in FAILURE_LABELS:
        lines.append(f"| {label} | {counts.get(label, 0)} | {baseline[label]:.1%} |")

    for dimension, breakdown in (
        ("Question type", by_type), ("Difficulty", by_difficulty), ("Document", by_document)
    ):
        lines += ["", f"## {dimension}\n", "| group | n_q | n_obs | worst over-represented failure |", "|---|---|---|---|"]
        for name in sorted(breakdown, key=lambda g: breakdown[g]["n_questions"], reverse=True):
            stats = breakdown[name]
            flag = " **(small sample)**" if stats["n_questions"] <= SMALL_SAMPLE_QUESTIONS else ""
            lifts = {label: lift(rate, baseline[label]) for label, rate in stats["rates"].items() if rate > 0}
            worst = max(lifts, key=lambda label: lifts[label] or 0) if lifts else None
            desc = (f"{worst} ({stats['rates'][worst]:.0%}, {lifts[worst]:.1f}x overall)"
                    if worst else "—")
            lines.append(f"| {name}{flag} | {stats['n_questions']} | {stats['n_observations']} | {desc} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved -> {OUT_MD}")


def main() -> None:
    rows = load_600_rows()
    questions = {r["question_id"]: r for r in phase7a_lib._read_rows(QUESTIONS_CSV)}
    doc_map = question_to_document(phase7a_lib.load_evidence_rows())

    for row in rows:
        row["question_type"] = questions[row["question_id"]]["question_type"]
        row["document"] = doc_map.get(row["question_id"], "?")

    baseline = overall_rates(rows)
    print(f"Phase 8 failure analysis — chunk_size={CHUNK_SIZE}, "
          f"{len(rows)} observations (3 runs x 25 questions)\n")
    print("overall taxonomy:")
    counts = Counter(row["failure_label"] for row in rows)
    for label in FAILURE_LABELS:
        print(f"  {label:<32}{counts.get(label, 0):>3} ({baseline[label]:.1%})")

    by_type = breakdown_by(rows, lambda r: r["question_type"])
    by_difficulty = breakdown_by(rows, lambda r: r["difficulty"])
    by_document = breakdown_by(rows, lambda r: r["document"])

    print_breakdown("BY QUESTION TYPE", by_type, baseline)
    print_breakdown("BY DIFFICULTY", by_difficulty, baseline)
    print_breakdown("BY DOCUMENT", by_document, baseline)

    write_artifacts(rows, by_type, by_difficulty, by_document, baseline)


if __name__ == "__main__":
    main()
