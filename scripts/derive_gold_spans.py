"""Derive fixed source-document character offsets for every gold evidence row.

Run from the project root:
    ./.venv/bin/python -u scripts/derive_gold_spans.py

Writes data/evaluation/evidence_spans.csv — a DERIVED artefact. Never edit it
by hand and never type an offset into evidence.csv. Offsets are a mechanical
consequence of the already-verified evidence_text plus the PDF extraction; if
either changes, re-run this and the offsets follow. A hand-entered number
would be unverifiable and would silently rot.

Every derived span is validated three ways before being written:

  1. round-trip   normalise(source[start:end]) == normalise(evidence_text)
  2. uniqueness   the snippet occurs exactly once on its VERIFIED pages
  3. sanity       0 <= start < end <= len(source)

Check 2 is per-page rather than per-document on purpose. Annual reports repeat
whole paragraphs verbatim between the Directors' Report and the MD&A — q010's
four snippets each appear on both p.43 and p.70 of the Ecoplast report — so
document-wide uniqueness is not achievable and would reject valid evidence.

Any failure aborts the whole run rather than writing a partial file. A gold
set that is 90% correct is worse than one that refuses to build, because the
missing 10% is invisible in every downstream number.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluation import normalise, normalised_with_offsets  # noqa: E402
from src.ingestion import load_pdf_pages, source_text  # noqa: E402

DOCUMENTS_DIR = Path("data/documents")
EVIDENCE_CSV = Path("data/evaluation/evidence.csv")
SPANS_CSV = Path("data/evaluation/evidence_spans.csv")


def page_ranges(pages: list[str]) -> list[tuple[int, int]]:
    """Character range of each page, matching split_into_chunks() exactly."""
    ranges, cursor = [], 0
    for page_text in pages:
        ranges.append((cursor, cursor + len(page_text)))
        cursor += len(page_text) + 1  # +1 for the "\n" join
    return ranges


def parse_pages(value: str) -> list[int]:
    """Read a relevant_pages cell: '70', '287-288', or '12,15'."""
    wanted: list[int] = []
    for part in value.replace(" ", "").split(","):
        if "-" in part:
            first, last = part.split("-")
            wanted.extend(range(int(first), int(last) + 1))
        elif part:
            wanted.append(int(part))
    return wanted


def derive_one(
    evidence_text: str,
    raw_source: str,
    ranges: list[tuple[int, int]],
    wanted_pages: list[int],
) -> tuple[int, int, int]:
    """Locate one snippet on its VERIFIED pages. Returns (start, end, matches).

    The search happens in NORMALISED space — PDF extraction sprays line breaks
    through the text, so the snippet is almost never a raw substring — and the
    result is mapped back to raw offsets through the index list.

    Occurrences outside the recorded pages are discarded. That is not a
    convenience: annual reports repeat whole paragraphs verbatim between the
    Directors' Report and the MD&A, so a snippet can legitimately appear twice.
    relevant_pages records which copy a human actually verified, and using it
    keeps the offsets derived from verified data rather than from a guess about
    which duplicate was meant.
    """
    normalised_source, offsets = normalised_with_offsets(raw_source)
    needle = normalise(evidence_text)

    # Character window covering the verified pages, widened by the snippet
    # length so a passage straddling a page break is not clipped out.
    lows = [ranges[p - 1][0] for p in wanted_pages if 1 <= p <= len(ranges)]
    highs = [ranges[p - 1][1] for p in wanted_pages if 1 <= p <= len(ranges)]
    if not lows:
        return -1, -1, 0
    margin = len(evidence_text) + 1
    window = (min(lows) - margin, max(highs) + margin)

    matches: list[tuple[int, int]] = []
    position = normalised_source.find(needle)
    while position != -1:
        start = offsets[position]
        # offsets[...-1] is the raw index of the LAST matched character, so the
        # exclusive end is one past it. Using offsets[position + len(needle)]
        # would over-run into the following character.
        end = offsets[position + len(needle) - 1] + 1
        if window[0] <= start <= window[1]:
            matches.append((start, end))
        position = normalised_source.find(needle, position + 1)

    if len(matches) != 1:
        return -1, -1, len(matches)
    return matches[0][0], matches[0][1], 1


def main() -> None:
    rows = list(csv.DictReader(EVIDENCE_CSV.open(encoding="utf-8")))
    print(f"deriving spans for {len(rows)} evidence rows\n")

    # Extract each PDF once; this is the slow part.
    sources: dict[str, str] = {}
    page_maps: dict[str, list[tuple[int, int]]] = {}
    for name in sorted({row["relevant_document"] for row in rows}):
        pages = load_pdf_pages(DOCUMENTS_DIR / name)
        sources[name] = source_text(pages)
        page_maps[name] = page_ranges(pages)
        print(f"  {name}: {len(pages)} pages, {len(sources[name]):,} chars")

    print()
    derived, failures = [], []
    for row in rows:
        document = row["relevant_document"]
        raw_source = sources[document]
        wanted_pages = parse_pages(row["relevant_pages"])
        start, end, occurrences = derive_one(
            row["evidence_text"], raw_source, page_maps[document], wanted_pages
        )

        if occurrences != 1:
            failures.append(
                f"{row['evidence_id']} ({row['question_id']}): found "
                f"{occurrences} occurrences on verified page(s) "
                f"{row['relevant_pages']} of {document} — "
                f"{'snippet is ambiguous there' if occurrences > 1 else 'snippet not found there'}"
            )
            continue

        if not (0 <= start < end <= len(raw_source)):
            failures.append(f"{row['evidence_id']}: nonsensical span [{start},{end})")
            continue

        # The round-trip is the real proof. Everything above could be right by
        # accident; this cannot.
        if normalise(raw_source[start:end]) != normalise(row["evidence_text"]):
            failures.append(f"{row['evidence_id']}: round-trip mismatch at [{start},{end})")
            continue

        derived.append(
            {
                "evidence_id": row["evidence_id"],
                "question_id": row["question_id"],
                # One required fact. Rows sharing a group_id are alternative
                # locations of it, each independently sufficient.
                "group_id": row["group_id"],
                "source_document": row["relevant_document"],
                "start_char": start,
                "end_char": end,
                "relevant_pages": row["relevant_pages"],
                "span_length": end - start,
            }
        )
        print(f"  {row['evidence_id']:<6}{row['group_id']:<10}"
              f"[{start:>8},{end:>8})  len={end - start:>4}")

    if failures:
        print(f"\n{len(failures)} FAILURES — nothing written:")
        for failure in failures:
            print(f"  {failure}")
        raise SystemExit(1)

    with SPANS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(derived[0]))
        writer.writeheader()
        writer.writerows(derived)

    lengths = sorted(row["span_length"] for row in derived)
    print(f"\nall {len(derived)} spans derived and validated -> {SPANS_CSV}")
    print(f"span length: min={lengths[0]} median={lengths[len(lengths) // 2]} max={lengths[-1]}")


if __name__ == "__main__":
    main()
