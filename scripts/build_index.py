"""Rebuild the Chroma index from scratch over every PDF in data/documents.

Run from the project root:
    ./.venv/bin/python -u scripts/build_index.py
    ./.venv/bin/python -u scripts/build_index.py --chunk-size 300 --overlap 50

The -u matters: without it Python buffers stdout and a 20-minute build looks
frozen. Deletes and recreates the collection, so it is safe to re-run.

CLI parameters exist so Phase 7A can sweep chunk_size without editing module
constants between runs — mutating CHUNK_SIZE in src/ingestion.py between
configurations would make "what config actually built this index" a fact
nobody could verify after the fact. Every value here has an explicit default
equal to the module constant, so a bare invocation behaves exactly as before.
"""

import argparse
import sys
import time
from pathlib import Path

# Python puts the SCRIPT's folder on sys.path, not the folder you ran it from,
# so `import src...` fails without this. Adding the project root explicitly
# keeps the script runnable with a plain `python scripts/build_index.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

# Explicit path, not bare load_dotenv(): the no-argument form walks the call
# stack to guess the caller's directory and raises when there is no frame.
load_dotenv(Path(".env"))

from src.ingestion import CHUNK_OVERLAP, CHUNK_SIZE, build_index  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Separated from main() so tests can inspect defaults without running a build."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents-dir", type=Path, default=Path("data/documents"))
    parser.add_argument("--store-dir", type=Path, default=Path("data/chroma"))
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE,
                        help=f"default: {CHUNK_SIZE} (src.ingestion.CHUNK_SIZE)")
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP,
                        help=f"default: {CHUNK_OVERLAP} (src.ingestion.CHUNK_OVERLAP)")
    parser.add_argument("--only", nargs="*", default=None,
                        help="restrict to these PDF filenames (default: every PDF)")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    started = time.time()
    total = build_index(
        documents_dir=args.documents_dir,
        store_dir=args.store_dir,
        only=args.only,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        show_progress=not args.quiet,
    )
    elapsed = time.time() - started

    # Machine-parseable summary line, separate from the human progress log
    # build_index() already prints — this is what the Phase 7A orchestration
    # reads to record build_time_seconds without scraping prose.
    print(f"RESULT chunk_size={args.chunk_size} overlap={args.overlap} "
          f"store_dir={args.store_dir} total_chunks={total} seconds={elapsed:.2f}")


if __name__ == "__main__":
    main()
