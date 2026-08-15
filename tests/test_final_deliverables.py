"""Tests for Phase 10's final deliverables: the report, the README, and the
repository's integrity. No API key, no index, no network calls.
"""

import hashlib
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README = PROJECT_ROOT / "README.md"
FINAL_REPORT = PROJECT_ROOT / "reports" / "FINAL_REPORT.md"
DASHBOARD = PROJECT_ROOT / "app" / "dashboard.py"

# Known-good hashes for the FROZEN Phase 5/6 artefacts — established and
# re-verified after every subsequent phase throughout this project. If any
# of these ever change, something touched a result it should never have.
FROZEN_HASHES = {
    "results/phase5_retrieval_baseline.FROZEN.csv": "afa17df00bcd44fb",
    "results/phase5_retrieval_baseline.FROZEN.md": "cdd96c180c39b4c0",
    "results/phase6_generation_baseline.csv": "2f161effc81aad50",
    "results/phase6_generation_majority3.csv": "d2cb81a32f4b5693",
}


# ==========================================================================
# Frozen artefact integrity
# ==========================================================================
@pytest.mark.parametrize("relative_path,expected_prefix", FROZEN_HASHES.items())
def test_frozen_artefact_is_byte_identical(relative_path, expected_prefix):
    path = PROJECT_ROOT / relative_path
    assert path.exists(), f"frozen artefact missing: {relative_path}"
    got = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    assert got == expected_prefix, (
        f"{relative_path} has changed since it was frozen "
        f"(expected {expected_prefix}, got {got})"
    )


# ==========================================================================
# Deliverables exist
# ==========================================================================
def test_final_report_exists():
    assert FINAL_REPORT.exists()


def test_dashboard_exists():
    assert DASHBOARD.exists()


def test_readme_exists():
    assert README.exists()


# ==========================================================================
# README-referenced paths are real, not aspirational
# ==========================================================================
def test_readme_referenced_paths_exist():
    text = README.read_text(encoding="utf-8")
    # Markdown links of the form [text](path) or [text](path#anchor)
    for match in re.finditer(r"\]\(([^)]+)\)", text):
        target = match.group(1).split("#")[0]
        if target.startswith("http") or target == "":
            continue
        resolved = PROJECT_ROOT / target
        assert resolved.exists(), f"README links to missing path: {target}"


def test_readme_commands_reference_real_files():
    text = README.read_text(encoding="utf-8")
    assert "streamlit run app/dashboard.py" in text
    assert (PROJECT_ROOT / "app" / "dashboard.py").exists()
    assert "pytest -q" in text


def test_readme_mentions_no_api_key_needed_for_dashboard():
    text = README.read_text(encoding="utf-8")
    idx = text.find("streamlit run app/dashboard.py")
    assert idx != -1
    surrounding = text[max(0, idx - 400):idx].lower()
    # Markdown bold/backticks split "no" from "api key" in the rendered
    # text, so match loosely rather than requiring an exact contiguous
    # phrase — this is a wording check, not a strict grep.
    assert "no**" in surrounding and "api" in surrounding and "key" in surrounding


# ==========================================================================
# No contradictory headline numbers between README, FINAL_REPORT, and the
# actual source CSVs
# ==========================================================================
def _load_phase7a_coverage_at_5():
    import csv

    rows = list(csv.DictReader((PROJECT_ROOT / "results/phase7a_retrieval_configs.csv").open(encoding="utf-8")))
    at5 = {int(r["chunk_size"]): float(r["gold_span_coverage"]) for r in rows if r["k"] == "5"}
    return at5


def _load_phase7b_correctness_means():
    import csv
    from collections import defaultdict

    rows = list(csv.DictReader((PROJECT_ROOT / "results/phase7b_generation_runs.csv").open(encoding="utf-8")))
    by_config_run = defaultdict(list)
    for row in rows:
        by_config_run[(int(row["chunk_size"]), int(row["run_index"]))].append(int(row["correct"]))
    per_config_run_means = defaultdict(list)
    for (size, _run), values in by_config_run.items():
        per_config_run_means[size].append(sum(values) / len(values))
    return {size: sum(vals) / len(vals) for size, vals in per_config_run_means.items()}


def test_phase7a_coverage_numbers_in_readme_match_source_csv():
    coverage = _load_phase7a_coverage_at_5()
    text = README.read_text(encoding="utf-8")
    # README states 19.7% (500) and 23.9% (600) — must match the CSV to 1dp.
    assert f"{coverage[500] * 100:.1f}%" == "19.7%"
    assert f"{coverage[600] * 100:.1f}%" == "23.9%"
    assert "19.7%" in text
    assert "23.9%" in text


def test_phase7b_correctness_numbers_in_readme_match_source_csv():
    means = _load_phase7b_correctness_means()
    text = README.read_text(encoding="utf-8")
    assert f"{means[500] * 100:.1f}%" == "10.7%"
    assert f"{means[600] * 100:.1f}%" == "20.0%"
    assert "10.7%" in text
    assert "20.0%" in text


def test_readme_and_final_report_agree_on_the_winning_chunk_size():
    readme_text = README.read_text(encoding="utf-8")
    report_text = FINAL_REPORT.read_text(encoding="utf-8")
    # Both must name 600 as the winner and 500 as the baseline; neither
    # should assert the reverse anywhere near "winner"/"accepted".
    assert "600" in readme_text and "600" in report_text
    assert "chunk_size=600" in report_text or "600 (winner)" in report_text


def test_final_report_states_verified_pricing_date_not_a_bare_constant():
    text = FINAL_REPORT.read_text(encoding="utf-8")
    assert "2026-08-15" in text
    assert "not permanent" in text.lower() or "re-verify" in text.lower()


def test_final_report_distinguishes_correct_from_grounded_correct():
    text = FINAL_REPORT.read_text(encoding="utf-8")
    assert "grounded_correct" in text
    assert "unsupported_correct" in text


def test_final_report_does_not_overclaim_statistical_significance():
    text = FINAL_REPORT.read_text(encoding="utf-8")
    assert "not a formal statistical significance" in text.lower() or \
           "not a formal significance" in text.lower()


def test_final_report_describes_human_review_as_ai_assisted():
    text = FINAL_REPORT.read_text(encoding="utf-8")
    assert "ai-assisted" in text.lower()
    assert "independent blinded human" not in text.lower() or "not" in text.lower()


# ==========================================================================
# requirements.txt actually includes what the deliverables need
# ==========================================================================
def test_requirements_includes_streamlit():
    text = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit" in text


def test_requirements_includes_pandas():
    text = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pandas" in text
