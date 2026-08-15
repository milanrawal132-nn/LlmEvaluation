"""Shared logic for Phase 9: cost, latency, and efficiency analysis.

Works entirely from ALREADY-CAPTURED artefacts:
    results/phase7a_retrieval_configs.csv   (index-side: chunks, size, build time)
    results/phase7b_generation_runs.csv     (generation-side: tokens, latency, quality)

No index is built and no generation call is made here — every number in this
file is a re-aggregation of numbers Phase 7A/7B already measured and saved.

Pricing is a CONVERSION LAYER, not a measurement. Token counts are the
source-of-truth data; dollar figures are computed only from an explicitly
verified price, recorded with its source and check date, never from a
constant reused silently. See VerifiedPricing below.
"""

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

RESULTS_DIR = Path("results")
PHASE7A_CSV = RESULTS_DIR / "phase7a_retrieval_configs.csv"
PHASE7B_CSV = RESULTS_DIR / "phase7b_generation_runs.csv"

EFFICIENCY_CSV = RESULTS_DIR / "phase9_efficiency.csv"
EFFICIENCY_MD = RESULTS_DIR / "phase9_efficiency.md"
LATENCY_CSV = RESULTS_DIR / "phase9_latency_by_answer.csv"

CONFIGS = (500, 600)


def _read_rows(path: Path) -> list[dict]:
    """Tolerant of the stray leading blank line documented for evidence.csv;
    harmless no-op on files that don't have one (both Phase 7A/7B CSVs)."""
    lines = [line for line in path.open(encoding="utf-8") if line.strip()]
    return list(csv.DictReader(lines))


# --------------------------------------------------------------------------
# Verified pricing — explicit, sourced, dated. Never a silent constant reuse.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class VerifiedPricing:
    model: str
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    date_checked: str
    source: str


def cost_usd(input_tokens: int, output_tokens: int, pricing: VerifiedPricing | None = None) -> float | None:
    """None when pricing is unverified — the caller must handle that, not
    silently substitute a stale or invented number."""
    if pricing is None:
        return None
    return (input_tokens / 1_000_000 * pricing.input_cost_per_mtok
            + output_tokens / 1_000_000 * pricing.output_cost_per_mtok)


# --------------------------------------------------------------------------
# Phase 7A: index-side efficiency (already measured, just re-presented)
# --------------------------------------------------------------------------
def load_index_stats() -> dict[int, dict]:
    """One row per chunk_size (dedupe the 4 K-rows Phase 7A stored)."""
    rows = _read_rows(PHASE7A_CSV)
    by_size: dict[int, dict] = {}
    for row in rows:
        size = int(row["chunk_size"])
        if size not in by_size:
            by_size[size] = {
                "chunk_count": int(row["chunk_count"]),
                "index_size_mb": float(row["index_size_mb"]),
                "build_time_seconds": float(row["build_time_seconds"]),
            }
    return by_size


def pct_diff(new: float, old: float) -> float | None:
    """(new - old) / old, as a fraction. None when old is 0 — a percentage
    change from zero is undefined, not infinite or zero."""
    if old == 0:
        return None
    return (new - old) / old


def index_efficiency_comparison(index_stats: dict[int, dict]) -> dict:
    base, winner = index_stats[500], index_stats[600]
    comparison = {}
    for metric in ("chunk_count", "index_size_mb", "build_time_seconds"):
        comparison[metric] = {
            "500": base[metric],
            "600": winner[metric],
            "abs_diff": winner[metric] - base[metric],
            "pct_diff": pct_diff(winner[metric], base[metric]),
        }
    return comparison


# --------------------------------------------------------------------------
# Phase 7B: generation-side token / latency / quality aggregation
# --------------------------------------------------------------------------
def load_generation_rows() -> list[dict]:
    rows = _read_rows(PHASE7B_CSV)
    for row in rows:
        row["input_tokens"] = int(row["input_tokens"])
        row["output_tokens"] = int(row["output_tokens"])
        row["latency_seconds"] = float(row["latency_seconds"])
        row["correct"] = int(row["correct"])
        row["faithful"] = int(row["faithful"])
        row["relevant"] = int(row["relevant"])
        row["abstained"] = int(row["abstained"])
    return rows


def rows_for_config(rows: list[dict], chunk_size: int) -> list[dict]:
    return [row for row in rows if int(row["chunk_size"]) == chunk_size]


def rows_by_run(config_rows: list[dict]) -> dict[int, list[dict]]:
    by_run: dict[int, list[dict]] = {}
    for row in config_rows:
        by_run.setdefault(int(row["run_index"]), []).append(row)
    return by_run


def token_stats(config_rows: list[dict]) -> dict:
    """Total/mean/median input and output tokens, pooled across all 3 runs
    (75 observations) — the denominators explicitly stated per §2."""
    inputs = [row["input_tokens"] for row in config_rows]
    outputs = [row["output_tokens"] for row in config_rows]
    return {
        "n": len(config_rows),
        "total_input_tokens": sum(inputs),
        "mean_input_tokens": statistics.mean(inputs),
        "median_input_tokens": statistics.median(inputs),
        "total_output_tokens": sum(outputs),
        "mean_output_tokens": statistics.mean(outputs),
        "median_output_tokens": statistics.median(outputs),
        "total_tokens": sum(inputs) + sum(outputs),
    }


def tokens_by_run(config_rows: list[dict]) -> dict[int, dict]:
    return {
        run_index: {
            "input_tokens": sum(row["input_tokens"] for row in rows),
            "output_tokens": sum(row["output_tokens"] for row in rows),
        }
        for run_index, rows in rows_by_run(config_rows).items()
    }


def tokens_per_success(config_rows: list[dict], success_field: str) -> float | None:
    """Total input tokens spent divided by the number of successes.

    None (not 0, not inf) when there are zero successes: dividing by zero
    successes is undefined, and reporting 0 would misleadingly imply the
    tokens were free.
    """
    successes = sum(row[success_field] for row in config_rows)
    if successes == 0:
        return None
    total_input = sum(row["input_tokens"] for row in config_rows)
    return total_input / successes


def latency_stats(config_rows: list[dict]) -> dict:
    values = [row["latency_seconds"] for row in config_rows]
    n = len(values)
    sorted_values = sorted(values)
    # p90 needs a reasonable sample to mean anything; n=75 qualifies.
    p90_index = min(n - 1, int(round(0.90 * (n - 1))))
    return {
        "n": n,
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.stdev(values) if n > 1 else 0.0,
        "p90": sorted_values[p90_index],
        "total_wall_clock": sum(values),
    }


def latency_by_run(config_rows: list[dict]) -> dict[int, dict]:
    return {run_index: latency_stats(rows) for run_index, rows in rows_by_run(config_rows).items()}


# --------------------------------------------------------------------------
# Quality-efficiency ratios
# --------------------------------------------------------------------------
def rate(config_rows: list[dict], field: str) -> float:
    return sum(row[field] for row in config_rows) / len(config_rows) if config_rows else 0.0


def per_1000_input_tokens(config_rows: list[dict], success_field: str) -> float:
    """successes per 1000 input tokens spent — a throughput-per-spend ratio,
    the inverse framing of tokens_per_success (and easier to compare configs
    that differ in absolute token volume)."""
    total_input = sum(row["input_tokens"] for row in config_rows)
    successes = sum(row[success_field] for row in config_rows)
    if total_input == 0:
        return 0.0
    return successes / (total_input / 1000)


def per_second_latency(config_rows: list[dict], success_field: str) -> float:
    total_latency = sum(row["latency_seconds"] for row in config_rows)
    successes = sum(row[success_field] for row in config_rows)
    if total_latency == 0:
        return 0.0
    return successes / total_latency
