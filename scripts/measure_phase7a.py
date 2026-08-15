"""Phase 7A: measure ONE chunk-size configuration against an already-built index.

Run from the project root, AFTER building the index for this configuration
(scripts/build_index.py --chunk-size N --overlap 50):

    ./.venv/bin/python -u scripts/measure_phase7a.py \\
        --chunk-size 500 --overlap 50 --store-dir data/chroma \\
        --build-time-seconds 552.9

This script does NOT build or delete the index — the orchestration around it
does, because only one index fits on disk at a time. It only measures, using
the CURRENT gold set (25 questions / 35 evidence rows / 30 groups) and
group-aware span metrics, then upserts its results into the durable Phase 7A
CSVs so re-running one configuration never disturbs the others.

Fails fast, before any retrieval call, if:
  - the gold set has drifted from its expected shape
  - the index's chunk count disagrees with a local recount for this config
  - retrieved chunks carry no start_char/end_char
  - any gold-evidence GROUP is structurally unreachable at this chunk size
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

import scripts.phase7a_lib as lib  # noqa: E402
from src.ingestion import COLLECTION_NAME  # noqa: E402
from src.retrieval import retrieve  # noqa: E402


def index_size_mb(store_dir: Path) -> float:
    total_bytes = sum(f.stat().st_size for f in store_dir.rglob("*") if f.is_file())
    return total_bytes / (1024 * 1024)


def verify_index_config(store_dir: Path, local: lib.LocalChunking) -> int:
    """Confirm the built index actually matches the requested config.

    The only trustworthy check is a recount from the SAME chunking function
    that built the index, compared against what Chroma actually stored —
    trusting the build log alone would miss a build that silently used stale
    module defaults.
    """
    client = chromadb.PersistentClient(path=str(store_dir))
    collection = client.get_collection(COLLECTION_NAME)
    stored_count = collection.count()

    if stored_count != local.total_chunk_count:
        raise SystemExit(
            f"index config mismatch: index holds {stored_count:,} chunks, but "
            f"chunk_size={local.chunk_size}/overlap={local.overlap} over the "
            f"current corpus locally recomputes to {local.total_chunk_count:,}. "
            f"This index was NOT built with the requested config."
        )

    sample = collection.get(limit=5, include=["metadatas"])
    required = {"source_document", "chunk_index", "pages", "start_char", "end_char"}
    for meta in sample["metadatas"]:
        missing = required - set(meta)
        if missing:
            raise SystemExit(f"metadata missing {missing} on a sampled chunk: {meta}")

    return stored_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, required=True)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--store-dir", type=Path, default=Path("data/chroma"))
    parser.add_argument("--build-time-seconds", type=float, required=True,
                        help="elapsed build time reported by scripts/build_index.py")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--distance-metric", default="cosine")
    args = parser.parse_args()

    print(f"{'=' * 66}\nPHASE 7A — chunk_size={args.chunk_size} overlap={args.overlap}\n{'=' * 66}")

    print("gold-set integrity check...")
    lib.check_gold_set_integrity()
    print(f"  OK: {lib.EXPECTED_QUESTION_COUNT} questions, "
          f"{lib.EXPECTED_EVIDENCE_ROW_COUNT} evidence rows, "
          f"{lib.EXPECTED_EVIDENCE_GROUP_COUNT} groups\n")

    print("local re-chunk (no API calls) for verification + static diagnostics...")
    local = lib.chunk_locally(args.chunk_size, args.overlap)
    print(f"  {local.total_chunk_count:,} chunks computed locally\n")

    print("verifying the built index matches this config...")
    chunk_count = verify_index_config(args.store_dir, local)
    print(f"  OK: index holds {chunk_count:,} chunks, offsets present\n")

    print("structural reachability (independent of embeddings)...")
    reach = lib.compute_reachability(local)
    print(f"  span_unreachable_groups = {reach.unreachable_groups}")
    print(f"  groups needing 1 / 2 / 3+ chunks (easiest alt): "
          f"{reach.groups_need_1_chunk} / {reach.groups_need_2_chunks} / "
          f"{reach.groups_need_3plus_chunks}")
    print(f"  legacy_unfindable_count (text ruler) = {reach.legacy_unfindable_count}\n")

    if reach.unreachable_groups > 0:
        raise SystemExit(
            f"ABORT: {reach.unreachable_groups} evidence group(s) are structurally "
            f"unreachable at chunk_size={args.chunk_size} — no combination of chunks "
            f"in the corpus covers them. Fix the gold set or the chunk size before "
            f"measuring; a coverage number here would be capped by the RULER, not "
            f"by retrieval."
        )

    size_mb = index_size_mb(args.store_dir)
    print(f"index size on disk: {size_mb:.1f} MB\n")

    print(f"scoring {lib.EXPECTED_QUESTION_COUNT} questions "
          f"(RANK_DEPTH={lib.RANK_DEPTH})...")
    questions = lib.load_questions()
    spans_by_question = lib.build_gold_spans()
    legacy_by_question = lib.build_legacy_evidence()

    def retrieve_fn(question_text: str, k: int):
        return retrieve(question_text, args.store_dir, k=k)

    per_k, rank_rows = lib.score_configuration(
        questions, spans_by_question, legacy_by_question, retrieve_fn
    )

    for row in per_k:
        row.update({
            "chunk_overlap": args.overlap,
            "embedding_model": args.embedding_model,
            "distance_metric": args.distance_metric,
            "chunk_count": chunk_count,
            "index_size_mb": round(size_mb, 1),
            "build_time_seconds": round(args.build_time_seconds, 1),
            "legacy_unfindable_count": reach.legacy_unfindable_count,
            "span_unreachable_groups": reach.unreachable_groups,
            "groups_need_1_chunk": reach.groups_need_1_chunk,
            "groups_need_2_chunks": reach.groups_need_2_chunks,
            "groups_need_3plus_chunks": reach.groups_need_3plus_chunks,
        })
        for key in ("document_recall", "gold_span_any_recall", "gold_span_coverage",
                    "legacy_any_evidence_recall", "legacy_evidence_coverage"):
            row[key] = round(row[key], 4)

    print(f"\n{'K':>4}{'DocRecall':>11}{'SpanAny':>10}{'SpanCov':>10}"
          f"{'LegAny':>9}{'LegCov':>9}")
    for row in per_k:
        print(f"{row['k']:>4}{row['document_recall']:>10.1%} "
              f"{row['gold_span_any_recall']:>9.1%} {row['gold_span_coverage']:>9.1%} "
              f"{row['legacy_any_evidence_recall']:>8.1%} {row['legacy_evidence_coverage']:>8.1%}")

    dist = lib.rank_distribution([r["first_rank"] or None for r in rank_rows])
    print(f"\nfirst gold span rank (depth={lib.RANK_DEPTH}): "
          f"median={dist['median']} mean={dist['mean']} "
          f"min={dist['min']} max={dist['max']} "
          f"none_found={dist['none_found_pct']:.0f}%")

    lib.upsert_config_rows(args.chunk_size, per_k)
    lib.upsert_rank_rows(args.chunk_size, rank_rows)
    print(f"\nsaved -> {lib.CONFIGS_CSV}")
    print(f"saved -> {lib.RANKS_CSV}")


if __name__ == "__main__":
    main()
