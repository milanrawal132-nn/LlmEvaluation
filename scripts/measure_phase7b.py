"""Phase 7B: end-to-end robustness — ONE configuration, N independent
generation runs, against an already-built index.

Run from the project root, AFTER building the index for this configuration:

    ./.venv/bin/python -u scripts/measure_phase7b.py --chunk-size 500 --runs 3
    ./.venv/bin/python -u scripts/measure_phase7b.py --chunk-size 600 --runs 3

Does NOT build or delete the index — orchestration around it does, since
only one index fits on disk at a time. Each run is a FRESH call to
generate() for every question — not a repeated judgement of one answer —
because the generator itself is non-deterministic; only repeated generation
exposes that noise.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

import scripts.phase7a_lib as phase7a_lib  # noqa: E402
import scripts.phase7b_lib as lib  # noqa: E402
from src.retrieval import retrieve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, required=True)
    parser.add_argument("--store-dir", type=Path, default=Path("data/chroma"))
    parser.add_argument("--runs", type=int, default=lib.DEFAULT_RUNS)
    args = parser.parse_args()

    print(f"{'=' * 66}\nPHASE 7B — chunk_size={args.chunk_size}, {args.runs} independent "
          f"generation runs\n{'=' * 66}")

    phase7a_lib.check_gold_set_integrity()
    questions = lib.load_questions()
    spans_by_question = lib.build_gold_spans()

    def retrieve_fn(question_text: str, k: int):
        return retrieve(question_text, args.store_dir, k=k)

    run_summaries = []
    accumulated: list[dict] = []  # every row for THIS chunk_size, across all runs so far
    for run_index in range(1, args.runs + 1):
        print(f"\n--- run {run_index}/{args.runs} ---")
        rows = []
        for i, question in enumerate(questions, start=1):
            row = lib.run_one(question, spans_by_question[question["question_id"]], retrieve_fn)
            row["run_index"] = run_index
            rows.append(row)
            print(f"  [{i:>2}/{len(questions)}] {row['question_id']}  "
                  f"ev={row['evidence_hit']} correct={row['correct']} "
                  f"faith={row['faithful']} abst={row['abstained']}  {row['failure_label']}")

        summary = lib.summarize_run(rows)
        run_summaries.append(summary)
        print(f"  run {run_index}: correct={summary['correct_rate']:.1%} "
              f"faithful={summary['faithful_rate']:.1%} "
              f"relevant={summary['relevant_rate']:.1%} "
              f"abstain={summary['abstain_rate']:.1%}")

        # upsert_raw_rows REPLACES all of this chunk_size's rows, so we must
        # pass the full accumulated set each time (not just this run) — a
        # crash mid-sweep then loses at most the in-progress run, never any
        # prior completed one, and no earlier run is ever silently dropped.
        accumulated.extend(rows)
        lib.upsert_raw_rows(args.chunk_size, accumulated)

    # Re-read what's actually on disk for this config (all runs) to compute
    # the final spread, since upserts above wrote incrementally.
    all_raw = phase7a_lib._read_rows(lib.RAW_CSV)
    config_rows = lib.rows_for_config(all_raw, args.chunk_size)
    by_run = lib.rows_by_run(config_rows)
    final_summaries = [lib.summarize_run(rows) for rows in by_run.values()]
    spread = lib.config_spread(final_summaries)

    print(f"\n{'=' * 66}\nSPREAD ACROSS {len(final_summaries)} RUNS "
          f"(chunk_size={args.chunk_size})\n{'=' * 66}")
    for metric, stats in spread.items():
        print(f"  {metric:<16} mean={stats['mean']:.1%}  "
              f"range=[{stats['min']:.1%}, {stats['max']:.1%}]  "
              f"spread={stats['range']:.1%}")

    print(f"\nsaved -> {lib.RAW_CSV}")


if __name__ == "__main__":
    main()
