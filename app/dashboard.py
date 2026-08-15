"""LLMEvalIQ dashboard — an offline, read-only view of a completed experiment.

Launch:
    streamlit run app/dashboard.py

This file NEVER calls an embedding API, a generation API, or builds/opens a
Chroma index. Every number it shows is loaded from results/*.csv and
data/evaluation/*.csv, already on disk from Phases 5-9. A reviewer can run
this with no OPENAI_API_KEY set at all.

Structure: pure loader/aggregation functions at module level (imported and
unit-tested with no Streamlit runtime needed), Streamlit rendering only
inside render_*()/main(), guarded by `if __name__ == "__main__"` so
`import app.dashboard` in a test never draws a page.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data" / "evaluation"

ACCEPTED_CONFIG = 600
BASELINE_CONFIG = 500

REQUIRED_ARTEFACTS = [
    "phase5_retrieval_baseline.FROZEN.csv",
    "phase7a_retrieval_configs.csv",
    "phase7a_first_span_ranks.csv",
    "phase7b_generation_runs.csv",
    "phase8_failure_breakdown.csv",
    "phase9_efficiency.csv",
]


# ==========================================================================
# Loaders — pure functions, no Streamlit calls. Tolerant of the stray
# leading blank line documented for evidence.csv (harmless no-op elsewhere).
# ==========================================================================
def _read_csv_tolerant(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    lines = [line for line in path.open(encoding="utf-8") if line.strip()]
    if not lines:
        return pd.DataFrame()
    return pd.read_csv(StringIO("".join(lines)))


def missing_artefacts(results_dir: Path = RESULTS_DIR) -> list[str]:
    """Which required Phase 5-9 files are absent — used to show a clear
    warning instead of a stack trace when the pipeline hasn't run yet."""
    return [name for name in REQUIRED_ARTEFACTS if not (results_dir / name).exists()]


def load_phase5_frozen() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase5_retrieval_baseline.FROZEN.csv")


def load_phase7a_configs() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase7a_retrieval_configs.csv")


def load_phase7a_ranks() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase7a_first_span_ranks.csv")


def load_phase7b_runs() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase7b_generation_runs.csv")


def load_phase8_breakdown() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase8_failure_breakdown.csv")


def load_phase9_efficiency() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase9_efficiency.csv")


def load_case_study_metrics() -> pd.DataFrame:
    return _read_csv_tolerant(RESULTS_DIR / "phase10_case_study_metrics.csv")


def load_questions() -> pd.DataFrame:
    return _read_csv_tolerant(DATA_DIR / "questions.csv")


# ==========================================================================
# Aggregation helpers — pure, testable, no Streamlit
# ==========================================================================
def phase5_metric_at_k(frozen: pd.DataFrame, k: int) -> dict:
    """Mean Document Recall / Any Evidence Recall / Coverage at one K, from
    the frozen Phase 5 per-question rows."""
    if frozen.empty:
        return {}
    return {
        "document_recall": frozen[f"doc_recall@{k}"].mean(),
        "any_evidence_recall": frozen[f"any_evidence@{k}"].mean(),
        "coverage": frozen[f"coverage@{k}"].mean(),
    }


def phase7a_at_k(configs: pd.DataFrame, k: int) -> pd.DataFrame:
    """One row per chunk_size, Phase 7A's metrics at a given K."""
    if configs.empty:
        return configs
    return configs[configs["k"] == k].sort_values("chunk_size").reset_index(drop=True)


def rank_distribution(ranks: pd.DataFrame, chunk_size: int) -> dict:
    """median/mean/min/max/none-found%, computed HERE from the raw per-
    question ranks — not a value copied out of a report."""
    subset = ranks[ranks["chunk_size"] == chunk_size]
    if subset.empty:
        return {}
    found = subset["first_rank"].dropna()
    n = len(subset)
    return {
        "median": found.median() if not found.empty else None,
        "mean": found.mean() if not found.empty else None,
        "min": found.min() if not found.empty else None,
        "max": found.max() if not found.empty else None,
        "none_found_pct": 100.0 * (n - len(found)) / n if n else None,
        "n_questions": n,
    }


def phase7b_run_summary(runs: pd.DataFrame, chunk_size: int) -> pd.DataFrame:
    """Per-run correctness/faithfulness/relevance/abstention rates for one
    config — the raw per-run numbers a mean-only view would hide."""
    subset = runs[runs["chunk_size"] == chunk_size]
    if subset.empty:
        return subset
    return (
        subset.groupby("run_index")[["correct", "faithful", "relevant", "abstained"]]
        .mean()
        .reset_index()
        .sort_values("run_index")
    )


def phase7b_spread(runs: pd.DataFrame, chunk_size: int) -> dict:
    per_run = phase7b_run_summary(runs, chunk_size)
    if per_run.empty:
        return {}
    return {
        metric: {"mean": per_run[metric].mean(), "min": per_run[metric].min(),
                 "max": per_run[metric].max()}
        for metric in ("correct", "faithful", "relevant", "abstained")
    }


def taxonomy_counts(runs: pd.DataFrame, chunk_size: int) -> pd.Series:
    subset = runs[runs["chunk_size"] == chunk_size]
    if subset.empty:
        return pd.Series(dtype=int)
    return subset["failure_label"].value_counts()


def failure_by_dimension(breakdown: pd.DataFrame, dimension: str, small_sample_max: int = 4) -> pd.DataFrame:
    """Phase 8's per-dimension breakdown, pivoted wide for a table, with a
    small-sample flag column carried through rather than dropped."""
    subset = breakdown[breakdown["dimension"] == dimension]
    if subset.empty:
        return subset
    pivot = subset.pivot_table(index=["group", "n_questions", "n_observations"],
                               columns="failure_label", values="rate", fill_value=0.0)
    pivot = pivot.reset_index()
    pivot["small_sample"] = pivot["n_questions"] <= small_sample_max
    return pivot.sort_values("n_questions", ascending=False)


def format_pct(value: float | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value * 100:.{decimals}f}%"


def format_pct_already(value: float | None, decimals: int = 1) -> str:
    """For values already expressed 0-100 (e.g. Phase 7A's *_pct fields)."""
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.{decimals}f}%"


# ==========================================================================
# Streamlit rendering — only executed when the file is actually run as a page
# ==========================================================================
def render_executive_overview(frozen, cfg, runs, eff) -> None:
    import streamlit as st

    st.subheader("Executive Overview")
    st.caption("Every number below is read from results/*.csv — nothing here is typed in.")

    p5 = phase5_metric_at_k(frozen, 5)
    winner_row = phase7a_at_k(cfg, 5)
    winner_cov = winner_row.loc[winner_row["chunk_size"] == ACCEPTED_CONFIG, "gold_span_coverage"]
    base_correct = phase7b_spread(runs, BASELINE_CONFIG).get("correct", {})
    win_correct = phase7b_spread(runs, ACCEPTED_CONFIG).get("correct", {})
    win_faith = phase7b_spread(runs, ACCEPTED_CONFIG).get("faithful", {})
    eff_row = eff[eff["chunk_size"] == ACCEPTED_CONFIG]
    base_eff_row = eff[eff["chunk_size"] == BASELINE_CONFIG]

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline Evidence Coverage@5 (500)", format_pct(p5.get("coverage")))
    c2.metric("Winning Gold Span Coverage@5 (600)",
              format_pct(winner_cov.iloc[0]) if not winner_cov.empty else "n/a")
    c3.metric("Chunk size accepted", f"{ACCEPTED_CONFIG} chars")

    c4, c5, c6 = st.columns(3)
    c4.metric("Baseline correctness (500, mean of 3 runs)", format_pct(base_correct.get("mean")))
    c5.metric("Winning correctness (600, mean of 3 runs)", format_pct(win_correct.get("mean")))
    c6.metric("Winning faithfulness (600, mean of 3 runs)", format_pct(win_faith.get("mean")))

    c7, c8 = st.columns(2)
    if not eff_row.empty and not base_eff_row.empty:
        c7.metric("Cost per correct answer — 600",
                  f"${eff_row['cost_per_correct_usd'].iloc[0]:.5f}")
        c8.metric("Cost per correct answer — 500",
                  f"${base_eff_row['cost_per_correct_usd'].iloc[0]:.5f}")

    st.info(
        "Document Recall was already 100% at K=5 for every chunk size tested — "
        "it carries no discriminating signal and was deliberately not used to "
        "pick the winning configuration. See the Retrieval tab.",
        icon="ℹ️",
    )
    st.warning(
        "25-question pilot, 3 companies of gold evidence, 3 generation runs. "
        "See Methodology & Limitations before treating any number here as a "
        "population estimate.",
        icon="⚠️",
    )


def render_retrieval(frozen, cfg, ranks) -> None:
    import streamlit as st

    st.subheader("Retrieval — chunk-size experiment (Phase 7A)")

    k = st.select_slider("K", options=sorted(cfg["k"].unique()), value=5)
    at_k = phase7a_at_k(cfg, k)

    st.markdown(f"**Gold Span Coverage vs Document Recall @ K={k}**")
    chart_df = at_k.set_index("chunk_size")[["document_recall", "gold_span_coverage", "gold_span_any_recall"]]
    st.bar_chart(chart_df)
    st.caption(
        "document_recall / gold_span_coverage / gold_span_any_recall, each a fraction "
        "0-1 (not a percent axis) — document_recall saturates at 1.0 for every "
        "configuration, which is exactly why it was not used to pick a winner."
    )

    st.dataframe(
        at_k[["chunk_size", "document_recall", "gold_span_any_recall", "gold_span_coverage",
              "chunk_count", "index_size_mb", "build_time_seconds"]]
        .rename(columns={"gold_span_coverage": "gold_span_coverage (selection metric)"}),
        width="stretch", hide_index=True,
    )

    st.markdown("**First Gold Span Rank distribution (depth=200)**")
    rank_rows = []
    for size in sorted(cfg["chunk_size"].unique()):
        dist = rank_distribution(ranks, size)
        if dist:
            rank_rows.append({"chunk_size": size, **dist})
    if rank_rows:
        rank_df = pd.DataFrame(rank_rows)
        st.dataframe(rank_df, width="stretch", hide_index=True)
        st.caption(
            "median/mean/min/max are computed over questions where SOME retrieved "
            "chunk touched the gold span within the top 200; none_found_pct is the "
            "share of the 25 questions where nothing did."
        )

    st.markdown("**Frozen Phase 5 baseline (500/50, the pre-experiment starting point)**")
    for kk in (1, 3, 5, 10):
        m = phase5_metric_at_k(frozen, kk)
        if m:
            st.write(f"K={kk}: Document Recall={format_pct(m['document_recall'])}  "
                     f"Any Evidence Recall={format_pct(m['any_evidence_recall'])}  "
                     f"Evidence Coverage={format_pct(m['coverage'])}")


def render_generation_robustness(runs) -> None:
    import streamlit as st

    st.subheader("Generation Robustness — 3 independent runs per configuration (Phase 7B)")
    st.caption(
        "The generator is non-deterministic. Every metric below is shown per-run, "
        "not averaged away — a single run cannot distinguish a real configuration "
        "effect from ordinary generation noise."
    )

    for size in (BASELINE_CONFIG, ACCEPTED_CONFIG):
        label = "Baseline (500)" if size == BASELINE_CONFIG else "Winner (600)"
        st.markdown(f"**{label}**")
        per_run = phase7b_run_summary(runs, size)
        if per_run.empty:
            st.write("no data")
            continue
        display = per_run.copy()
        for col in ("correct", "faithful", "relevant", "abstained"):
            display[col] = display[col].apply(format_pct)
        st.dataframe(display, width="stretch", hide_index=True)

        spread = phase7b_spread(runs, size)
        cols = st.columns(4)
        for i, metric in enumerate(("correct", "faithful", "relevant", "abstained")):
            s = spread.get(metric, {})
            cols[i].metric(
                metric.capitalize(),
                format_pct(s.get("mean")),
                delta=f"range {format_pct(s.get('min'))}–{format_pct(s.get('max'))}",
                delta_color="off",
            )

    st.markdown("**Failure taxonomy, pooled across all 3 runs (75 answers/config)**")
    tax = pd.DataFrame({
        "500": taxonomy_counts(runs, BASELINE_CONFIG),
        "600": taxonomy_counts(runs, ACCEPTED_CONFIG),
    }).fillna(0).astype(int)
    st.dataframe(tax, width="stretch")
    st.caption(
        "'correct' and 'grounded_correct' are NOT the same row: grounded_correct "
        "requires the retrieved context to actually support the answer. "
        "unsupported_correct (600 only) is never counted as a pipeline win."
    )


def render_failure_taxonomy(breakdown) -> None:
    import streamlit as st

    st.subheader("Failure Taxonomy — where failures concentrate (Phase 8)")
    st.caption("Computed at the accepted configuration (chunk_size=600), pooled over 3 runs.")

    for dimension, title in (
        ("document", "By document"), ("difficulty", "By difficulty"), ("question_type", "By question type")
    ):
        st.markdown(f"**{title}**")
        table = failure_by_dimension(breakdown, dimension)
        if table.empty:
            st.write("no data")
            continue
        small = table[table["small_sample"]]
        if not small.empty:
            st.warning(
                f"SMALL SAMPLE: {', '.join(small['group'].astype(str))} have "
                f"≤4 distinct questions — treat their rates as leads, not findings.",
                icon="⚠️",
            )
        display = table.drop(columns=["small_sample"]).set_index("group")
        pct_cols = [c for c in display.columns if c not in ("n_questions", "n_observations")]
        display[pct_cols] = display[pct_cols].map(format_pct)
        st.dataframe(display, width="stretch")


def render_case_studies(questions, runs, case_metrics) -> None:
    import streamlit as st

    st.subheader("Case Studies")

    cases = [
        (
            "q020", BASELINE_CONFIG,
            "Faithful but wrong — operating margin",
            "Faithfulness verifies the claim is IN the retrieved context, not that the "
            "RIGHT context was retrieved. The model read a real number off a real chunk "
            "and it was the wrong number.",
        ),
        (
            "q021", ACCEPTED_CONFIG,
            "Embedding-boundary / table-decoy failure",
            "At chunk_size=600, the chunk containing the correct answer (443 new "
            "clients / 1,965 client base) is fully intact — but a neighbouring "
            "client-tier TABLE, which does not contain either fact, embeds MORE "
            "similarly to the question and outranks it.",
        ),
        (
            "q023", ACCEPTED_CONFIG,
            "unsupported_correct — possible model recall",
            "Two independent numeric facts (84% AI-aware, 113 learning hours) both "
            "landed correct while the judge marked the answer unfaithful — i.e. not "
            "supported by whatever was actually retrieved. Two matching numbers by "
            "chance is unlikely; pretrained knowledge is the more plausible source.",
        ),
    ]

    q_lookup = questions.set_index("question_id") if not questions.empty else questions

    for qid, size, title, interpretation in cases:
        with st.expander(f"{qid} — {title}", expanded=False):
            if qid in getattr(q_lookup, "index", []):
                row = q_lookup.loc[qid]
                st.markdown(f"**Question:** {row['question']}")
                st.markdown(f"**Reference answer:** {row['reference_answer']}")
            answer_rows = runs[(runs["question_id"] == qid) & (runs["chunk_size"] == size)]
            if not answer_rows.empty:
                sample = answer_rows.iloc[0]
                st.markdown(f"**Model answer** (chunk_size={size}, run {sample['run_index']}): "
                            f"{sample['answer']}")
                st.markdown(f"**Failure label:** `{sample['failure_label']}`")
            st.markdown(f"**Interpretation:** {interpretation}")

            metrics = case_metrics[case_metrics["question_id"] == qid] if not case_metrics.empty else case_metrics
            if not metrics.empty:
                st.markdown("**Supporting measurements:**")
                st.dataframe(
                    metrics[["metric", "value", "unit", "note"]],
                    width="stretch", hide_index=True,
                )


def render_efficiency(cfg, eff) -> None:
    import streamlit as st

    st.subheader("Efficiency — index, tokens, latency, cost (Phase 9)")
    st.caption(
        "Pricing verified 2026-08-15 against OpenAI's official pricing page — "
        "re-verify before reusing these dollar figures later; token counts remain "
        "valid regardless of pricing changes."
    )

    display = eff.copy()
    for col in ("total_cost_usd", "mean_cost_usd", "cost_per_correct_usd", "cost_per_grounded_correct_usd"):
        if col in display.columns:
            display[col] = display[col].apply(lambda v: f"${v:.5f}" if pd.notna(v) and v != "" else "n/a")
    st.dataframe(display, width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Index efficiency (600 vs 500)**")
        idx_chart = cfg[cfg["k"] == 5].set_index("chunk_size")[["chunk_count", "index_size_mb"]]
        st.bar_chart(idx_chart)
    with c2:
        st.markdown("**Mean input tokens per answer**")
        tok_chart = eff.set_index("chunk_size")[["mean_input_tokens"]]
        st.bar_chart(tok_chart)

    st.info(
        "Retrieval query latency was not captured during Phase 7A and is not "
        "shown here — only generation latency was measured.",
        icon="ℹ️",
    )


def render_methodology() -> None:
    import streamlit as st

    st.subheader("Methodology & Limitations")
    st.markdown("""
**Gold evidence-group model.** Each question requires one or more *groups* (distinct
facts). Each group may have several *alternative* valid source locations — e.g. q019's
EPS figure appears in two different tables; q010's four facts each appear on two
different pages. Coverage is `max` over a group's alternatives (finding either copy
fully satisfies it — a duplicate earns no extra credit and its absence is no penalty),
combined `mean` (mode=`all`) or `max` (mode=`any`) across a question's required groups.

**Why row-level text matching was insufficient.** A chunk-size-dependent ruler cannot
fairly compare chunk sizes — text substring matching made some gold snippets
structurally unfindable at some chunk sizes and not others. Fixed source-document
character offsets, derived from the verified evidence text and validated by
round-tripping through the source PDF, fixed this.

**Limitations** (full detail in `reports/FINAL_REPORT.md`, Section 14):
- 25-question pilot gold set, evidence anchored in only 3 of 12 corpus documents
- One embedding model, one generation model, four chunk sizes, fixed overlap=50 and TOP_K=5
- No formal statistical significance test anywhere in this project
- No retrieval query-latency benchmark
- Faithfulness judge agreement with manual review = 92%, not 100%
- Manual review labels are **AI-assisted manual review**, not independent blinded human annotation
- Training-data recall risk is observed, not theoretical (`unsupported_correct` cases exist)
- Annual reports are a specialized, table-heavy document domain
""")
    st.markdown("[Full technical report →](../reports/FINAL_REPORT.md)")


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="LLMEvalIQ", page_icon="📊", layout="wide")
    st.title("LLMEvalIQ — RAG Evaluation Dashboard")
    st.caption(
        "Offline view of a completed experiment. No API key required — every "
        "number here is loaded from results/*.csv, produced by Phases 5-9."
    )

    missing = missing_artefacts()
    if missing:
        st.error(
            "Missing result artefacts — run the corresponding scripts first:\n\n"
            + "\n".join(f"- `{name}`" for name in missing)
        )
        st.stop()

    frozen = load_phase5_frozen()
    cfg = load_phase7a_configs()
    ranks = load_phase7a_ranks()
    runs = load_phase7b_runs()
    breakdown = load_phase8_breakdown()
    eff = load_phase9_efficiency()
    questions = load_questions()
    case_metrics = load_case_study_metrics()

    tabs = st.tabs([
        "Executive Overview", "Retrieval", "Generation Robustness",
        "Failure Taxonomy", "Case Studies", "Efficiency", "Methodology & Limitations",
    ])
    with tabs[0]:
        render_executive_overview(frozen, cfg, runs, eff)
    with tabs[1]:
        render_retrieval(frozen, cfg, ranks)
    with tabs[2]:
        render_generation_robustness(runs)
    with tabs[3]:
        render_failure_taxonomy(breakdown)
    with tabs[4]:
        render_case_studies(questions, runs, case_metrics)
    with tabs[5]:
        render_efficiency(cfg, eff)
    with tabs[6]:
        render_methodology()


if __name__ == "__main__":
    main()
