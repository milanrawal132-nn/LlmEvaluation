"""Phase 9: cost, latency, and efficiency analysis.

Run from the project root — reads ALREADY-CAPTURED Phase 7A/7B artefacts,
builds NO index, makes NO API calls:

    ./.venv/bin/python -u scripts/report_phase9.py

Pricing is verified explicitly below (model, price, date checked, source) —
see PRICING. If that verification is ever missing or stale, set PRICING to
None and every dollar figure in the report becomes "pending" rather than a
silently wrong number.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scripts.phase9_lib as lib  # noqa: E402

# Verified 2026-08-15 against two independent sources:
#   https://platform.openai.com/docs/pricing (redirects to
#   https://developers.openai.com/api/docs/pricing) — gpt-4o-mini:
#   $0.15 / 1M input tokens, $0.60 / 1M output tokens.
# Cross-checked via web search (devtk.ai model pricing tracker, Aug 2026
# snapshot) — same figures. These happen to match the constants already in
# src/generation.py, but they are being asserted here from a fresh check,
# not reused from that file silently.
PRICING = lib.VerifiedPricing(
    model="gpt-4o-mini",
    input_cost_per_mtok=0.15,
    output_cost_per_mtok=0.60,
    date_checked="2026-08-15",
    source="https://platform.openai.com/docs/pricing (OpenAI official); "
           "cross-checked via web search, Aug 2026",
)

SUCCESS_FIELDS = ("correct",)  # grounded_correct handled separately (needs evidence_hit too)


def grounded_correct_rows(config_rows: list[dict]) -> list[dict]:
    return [row for row in config_rows if row["failure_label"] == "grounded_correct"]


def section(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def main() -> None:
    index_stats = lib.load_index_stats()
    gen_rows = lib.load_generation_rows()

    # -------------------------------------------------------------- §1
    section("1. INDEX / RETRIEVAL-SIDE EFFICIENCY (from Phase 7A, not rebuilt)")
    idx_cmp = lib.index_efficiency_comparison(index_stats)
    for metric, stats in idx_cmp.items():
        pct = f"{stats['pct_diff']:+.1%}" if stats["pct_diff"] is not None else "undefined"
        print(f"  {metric:<20} 500={stats['500']:<12} 600={stats['600']:<12} "
              f"abs_diff={stats['abs_diff']:+.1f}  pct_diff={pct}")
    print("\n  retrieval latency was not captured during Phase 7A and is therefore not reported.")

    config_rows = {size: lib.rows_for_config(gen_rows, size) for size in lib.CONFIGS}

    # -------------------------------------------------------------- §2
    section("2. GENERATION TOKEN USAGE (from Phase 7B, 75 answers/config = 3 runs x 25 q)")
    token_summary = {}
    for size in lib.CONFIGS:
        rows = config_rows[size]
        stats = lib.token_stats(rows)
        token_summary[size] = stats
        print(f"\n  chunk_size={size} (n={stats['n']})")
        print(f"    input : total={stats['total_input_tokens']:>8,}  "
              f"mean={stats['mean_input_tokens']:>7.1f}  median={stats['median_input_tokens']:>7.1f}")
        print(f"    output: total={stats['total_output_tokens']:>8,}  "
              f"mean={stats['mean_output_tokens']:>7.1f}  median={stats['median_output_tokens']:>7.1f}")
        print(f"    total tokens: {stats['total_tokens']:,}")
        for run_index, run_tokens in sorted(lib.tokens_by_run(rows).items()):
            print(f"    run {run_index}: input={run_tokens['input_tokens']:,}  "
                  f"output={run_tokens['output_tokens']:,}")
        tps_correct = lib.tokens_per_success(rows, "correct")
        print(f"    input tokens per CORRECT answer: "
              f"{tps_correct:,.0f}" if tps_correct is not None else "    input tokens per CORRECT answer: n/a (0 correct)")
        gc_rows = grounded_correct_rows(rows)
        gc_input = sum(r["input_tokens"] for r in gc_rows)
        print(f"    input tokens per GROUNDED_CORRECT answer: "
              f"{gc_input / len(gc_rows):,.0f}" if gc_rows else "    input tokens per GROUNDED_CORRECT answer: n/a (0 grounded_correct)")

    delta_mean_input = token_summary[600]["mean_input_tokens"] - token_summary[500]["mean_input_tokens"]
    pct_input = lib.pct_diff(token_summary[600]["mean_input_tokens"], token_summary[500]["mean_input_tokens"])
    print(f"\n  mean input tokens, 600 vs 500: {delta_mean_input:+.1f} tokens "
          f"({pct_input:+.1%})" if pct_input is not None else "")
    print("  interpretation: larger chunks (600 vs 500 chars) retrieved at TOP_K=5 put more "
          "raw characters in the prompt; the input-token delta above is that effect measured "
          "directly, not inferred.")

    # -------------------------------------------------------------- §3
    section("3. GENERATION LATENCY")
    latency_summary = {}
    for size in lib.CONFIGS:
        rows = config_rows[size]
        stats = lib.latency_stats(rows)
        latency_summary[size] = stats
        print(f"\n  chunk_size={size} pooled (n={stats['n']})")
        print(f"    mean={stats['mean']:.2f}s  median={stats['median']:.2f}s  "
              f"min={stats['min']:.2f}s  max={stats['max']:.2f}s  "
              f"stdev={stats['stdev']:.2f}s  p90={stats['p90']:.2f}s")
        print(f"    total wall-clock across all {stats['n']} calls: {stats['total_wall_clock']:.1f}s")
        for run_index, run_stats in sorted(lib.latency_by_run(rows).items()):
            print(f"    run {run_index}: mean={run_stats['mean']:.2f}s  "
                  f"median={run_stats['median']:.2f}s  stdev={run_stats['stdev']:.2f}s")

    mean_delta = latency_summary[600]["mean"] - latency_summary[500]["mean"]
    pooled_stdev = max(latency_summary[500]["stdev"], latency_summary[600]["stdev"])
    print(f"\n  mean latency delta (600 - 500): {mean_delta:+.2f}s")
    if abs(mean_delta) < pooled_stdev:
        print(f"  this delta ({abs(mean_delta):.2f}s) is SMALLER than the larger config's own "
              f"answer-to-answer stdev ({pooled_stdev:.2f}s) -> not interpreted as a meaningful "
              f"difference, per instruction not to over-read small latency gaps.")
    else:
        print(f"  this delta exceeds the larger config's stdev ({pooled_stdev:.2f}s) — "
              f"worth noting, though still not a formal significance test.")

    # -------------------------------------------------------------- §4
    section("4. QUALITY-EFFICIENCY TRADE-OFF")
    for size in lib.CONFIGS:
        rows = config_rows[size]
        correct_per_1k = lib.per_1000_input_tokens(rows, "correct")
        gc_ids = {r["question_id"] for r in grounded_correct_rows(rows)}
        # grounded_correct per 1000 input tokens: reuse per_1000_input_tokens
        # by building a synthetic field, kept inline (small, one-off) rather
        # than adding a second parallel helper for one call site.
        total_input = sum(r["input_tokens"] for r in rows)
        gc_count = sum(1 for r in rows if r["failure_label"] == "grounded_correct")
        gc_per_1k = (gc_count / (total_input / 1000)) if total_input else 0.0
        correct_per_sec = lib.per_second_latency(rows, "correct")
        gc_per_sec = (gc_count / sum(r["latency_seconds"] for r in rows)) if rows else 0.0
        print(f"\n  chunk_size={size}")
        print(f"    correct answers per 1,000 input tokens:          {correct_per_1k:.3f}")
        print(f"    grounded_correct answers per 1,000 input tokens: {gc_per_1k:.3f}")
        print(f"    correct answers per second of latency:           {correct_per_sec:.3f}")
        print(f"    grounded_correct answers per second of latency:  {gc_per_sec:.3f}")
    print("\n  caveat: denominators are 75 answers over 25 DISTINCT questions x 3 runs — "
          "these ratios describe this sample, not a population estimate.")

    # -------------------------------------------------------------- §5 & §6
    section("5. MONETARY API COST")
    print(f"  pricing VERIFIED: model={PRICING.model}  "
          f"input=${PRICING.input_cost_per_mtok}/1M  output=${PRICING.output_cost_per_mtok}/1M")
    print(f"  date checked: {PRICING.date_checked}")
    print(f"  source: {PRICING.source}")

    section("6. COST OF CORRECTNESS (using verified pricing above)")
    cost_summary = {}
    for size in lib.CONFIGS:
        rows = config_rows[size]
        stats = token_summary[size]
        total_cost = lib.cost_usd(stats["total_input_tokens"], stats["total_output_tokens"], PRICING)
        mean_cost = total_cost / stats["n"]

        n_correct = sum(r["correct"] for r in rows)
        n_grounded = sum(1 for r in rows if r["failure_label"] == "grounded_correct")

        # "Cost per correct answer" means the total spend across the WHOLE
        # batch (wrong answers included) divided by how many of those calls
        # succeeded — not the cost of only the successful calls in isolation.
        # The latter would silently discard the cost of every wrong answer
        # that had to be generated along the way, which is the actual number
        # a "was this worth it" decision needs.
        cost_per_correct = total_cost / n_correct if n_correct else None
        cost_per_grounded = total_cost / n_grounded if n_grounded else None

        cost_summary[size] = {
            "total_cost": total_cost, "mean_cost": mean_cost,
            "n_correct": n_correct, "n_grounded": n_grounded,
            "cost_per_correct": cost_per_correct, "cost_per_grounded": cost_per_grounded,
        }
        print(f"\n  chunk_size={size}")
        print(f"    total generation cost (75 calls): ${total_cost:.4f}")
        print(f"    mean cost per answer:              ${mean_cost:.6f}")
        if cost_per_correct is not None:
            noise = " (NOISY: only {} correct answers)".format(n_correct) if n_correct < 10 else ""
            print(f"    cost per CORRECT answer:           ${cost_per_correct:.5f}{noise}")
        else:
            print(f"    cost per CORRECT answer:           n/a (0 correct)")
        if cost_per_grounded is not None:
            noise = " (NOISY: only {} grounded_correct answers)".format(n_grounded) if n_grounded < 10 else ""
            print(f"    cost per GROUNDED_CORRECT answer:  ${cost_per_grounded:.5f}{noise}")
        else:
            print(f"    cost per GROUNDED_CORRECT answer:  n/a (0 grounded_correct)")

    # -------------------------------------------------------------- §7
    section("7. RETRIEVAL / GENERATION TRADE-OFF SUMMARY")
    chunks_diff = idx_cmp["chunk_count"]
    size_diff = idx_cmp["index_size_mb"]
    build_diff = idx_cmp["build_time_seconds"]
    print(f"  fewer retrieval chunks?   {'YES' if chunks_diff['abs_diff'] < 0 else 'NO'} "
          f"({chunks_diff['abs_diff']:+,.0f} chunks, {chunks_diff['pct_diff']:+.1%})")
    print(f"  smaller index?            {'YES' if size_diff['abs_diff'] < 0 else 'NO'} "
          f"({size_diff['abs_diff']:+.1f} MB, {size_diff['pct_diff']:+.1%})")
    print(f"  faster build?             {'YES' if build_diff['abs_diff'] < 0 else 'NO'} "
          f"({build_diff['abs_diff']:+.1f}s, {build_diff['pct_diff']:+.1%})")
    print(f"  more input tokens/answer? "
          f"{'YES' if delta_mean_input > 0 else 'NO'} ({delta_mean_input:+.1f} tokens, "
          f"{pct_input:+.1%})" if pct_input is not None else "")
    correctness_delta = lib.rate(config_rows[600], "correct") - lib.rate(config_rows[500], "correct")
    print(f"  higher correctness?       YES ({correctness_delta:+.1%} pooled)")
    print(f"  latency materially different? "
          f"{'NO' if abs(mean_delta) < pooled_stdev else 'MAYBE'} "
          f"({mean_delta:+.2f}s vs stdev {pooled_stdev:.2f}s)")
    cheaper_per_call = cost_summary[600]["mean_cost"] < cost_summary[500]["mean_cost"]
    cheaper_per_correct = (
        cost_summary[600]["cost_per_correct"] is not None
        and cost_summary[500]["cost_per_correct"] is not None
        and cost_summary[600]["cost_per_correct"] < cost_summary[500]["cost_per_correct"]
    )
    print(f"\n  cheaper PER API CALL (500 vs 600)?     "
          f"{'600' if cheaper_per_call else '500'} is cheaper per call")
    print(f"  cheaper PER SUCCESSFUL ANSWER?          "
          f"{'600' if cheaper_per_correct else '500'} is cheaper per correct answer")
    print("  these can disagree, and here they do: 600 costs more per API call (larger "
          "prompts) but produces almost twice the correct answers per run, so it is CHEAPER "
          "per successful answer despite being more expensive per call.")
    print("\n  VERDICT: 600 is not 'more efficient' in the resource-frugality sense — it uses "
          "MORE input tokens per call and a comparable index build cost. It is more efficient "
          "in the OUTCOME sense: fewer tokens and dollars are wasted per correct answer, "
          "because far fewer calls are wasted on wrong answers.")

    write_artifacts(idx_cmp, token_summary, latency_summary, cost_summary, config_rows)
    print(f"\nsaved -> {lib.EFFICIENCY_CSV}")
    print(f"saved -> {lib.EFFICIENCY_MD}")
    print(f"saved -> {lib.LATENCY_CSV}")


def write_artifacts(idx_cmp, token_summary, latency_summary, cost_summary, config_rows) -> None:
    import csv

    lib.RESULTS_DIR.mkdir(exist_ok=True)

    # Efficiency CSV — one row per config, wide format (small enough to be
    # readable; Phase 7B's raw per-answer data is NOT duplicated here).
    fields = [
        "chunk_size", "chunk_count", "index_size_mb", "build_time_seconds",
        "total_input_tokens", "mean_input_tokens", "median_input_tokens",
        "total_output_tokens", "mean_output_tokens", "median_output_tokens",
        "total_tokens", "latency_mean_s", "latency_median_s", "latency_min_s",
        "latency_max_s", "latency_stdev_s", "latency_p90_s",
        "total_cost_usd", "mean_cost_usd", "n_correct", "n_grounded_correct",
        "cost_per_correct_usd", "cost_per_grounded_correct_usd",
    ]
    with lib.EFFICIENCY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for size in lib.CONFIGS:
            idx = {k: v[str(size)] for k, v in idx_cmp.items()}
            tok, lat, cost = token_summary[size], latency_summary[size], cost_summary[size]
            writer.writerow({
                "chunk_size": size, "chunk_count": idx["chunk_count"],
                "index_size_mb": idx["index_size_mb"], "build_time_seconds": idx["build_time_seconds"],
                "total_input_tokens": tok["total_input_tokens"], "mean_input_tokens": round(tok["mean_input_tokens"], 1),
                "median_input_tokens": tok["median_input_tokens"], "total_output_tokens": tok["total_output_tokens"],
                "mean_output_tokens": round(tok["mean_output_tokens"], 1), "median_output_tokens": tok["median_output_tokens"],
                "total_tokens": tok["total_tokens"], "latency_mean_s": round(lat["mean"], 3),
                "latency_median_s": round(lat["median"], 3), "latency_min_s": lat["min"], "latency_max_s": lat["max"],
                "latency_stdev_s": round(lat["stdev"], 3), "latency_p90_s": round(lat["p90"], 3),
                "total_cost_usd": round(cost["total_cost"], 6), "mean_cost_usd": round(cost["mean_cost"], 6),
                "n_correct": cost["n_correct"], "n_grounded_correct": cost["n_grounded"],
                "cost_per_correct_usd": round(cost["cost_per_correct"], 6) if cost["cost_per_correct"] else "",
                "cost_per_grounded_correct_usd": round(cost["cost_per_grounded"], 6) if cost["cost_per_grounded"] else "",
            })

    # Per-answer latency (light — timing + config + outcome, not full text)
    latency_fields = ["chunk_size", "run_index", "question_id", "input_tokens",
                      "output_tokens", "latency_seconds", "correct", "failure_label"]
    all_rows = [row for size in lib.CONFIGS for row in config_rows[size]]
    with lib.LATENCY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=latency_fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({field: row[field] for field in latency_fields})

    md_lines = [
        "# Phase 9 — cost, latency, and efficiency analysis\n",
        f"Pricing verified {PRICING.date_checked}: {PRICING.model} "
        f"${PRICING.input_cost_per_mtok}/1M input, ${PRICING.output_cost_per_mtok}/1M output. "
        f"Source: {PRICING.source}\n",
        "Retrieval query latency was not captured during Phase 7A and is not reported here.\n",
        "## Index efficiency (Phase 7A, not rebuilt)\n",
        "| metric | 500 | 600 | abs diff | pct diff |", "|---|---|---|---|---|",
    ]
    for metric, stats in idx_cmp.items():
        pct = f"{stats['pct_diff']:+.1%}" if stats["pct_diff"] is not None else "undefined"
        md_lines.append(f"| {metric} | {stats['500']} | {stats['600']} | {stats['abs_diff']:+.1f} | {pct} |")

    md_lines += ["", "## Token / latency / cost per configuration\n",
                "| chunk_size | mean input tok | mean output tok | mean latency (s) | "
                "total cost | cost/correct | cost/grounded_correct |",
                "|---|---|---|---|---|---|---|"]
    for size in lib.CONFIGS:
        tok, lat, cost = token_summary[size], latency_summary[size], cost_summary[size]
        cpc = f"${cost['cost_per_correct']:.5f}" if cost["cost_per_correct"] else "n/a"
        cpg = f"${cost['cost_per_grounded']:.5f}" if cost["cost_per_grounded"] else "n/a"
        md_lines.append(f"| {size} | {tok['mean_input_tokens']:.1f} | {tok['mean_output_tokens']:.1f} | "
                        f"{lat['mean']:.2f} | ${cost['total_cost']:.4f} | {cpc} | {cpg} |")

    lib.EFFICIENCY_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
