"""Ask a free-form question against the indexed corpus.

Run from the project root, AFTER an index exists (scripts/build_index.py):

    ./.venv/bin/python -u scripts/ask.py "How many board meetings did Ecoplast hold?"

Uses the same retrieve() + generate() functions as every evaluation phase —
this is not a separate code path, so an answer here is exactly what the
pipeline would have produced if this question had been in the gold set.
Needs OPENAI_API_KEY (query embedding + one generation call).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.generation import answer_question  # noqa: E402
from src.retrieval import TOP_K  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="the question to ask")
    parser.add_argument("--store-dir", type=Path, default=Path("data/chroma"))
    parser.add_argument("--k", type=int, default=TOP_K)
    args = parser.parse_args()

    if not args.store_dir.exists():
        raise SystemExit(
            f"no index at {args.store_dir} — build one first:\n"
            f"  ./.venv/bin/python -u scripts/build_index.py --chunk-size 600 --overlap 50"
        )

    answer, chunks = answer_question(args.question, args.store_dir, k=args.k)

    print(f"Q: {args.question}\n")
    print(f"A: {answer.text}\n")
    print(f"({answer.input_tokens} input / {answer.output_tokens} output tokens, "
          f"${answer.cost_usd():.6f}, {answer.latency_seconds:.2f}s)\n")

    print(f"Retrieved {len(chunks)} chunks (top-{args.k}):")
    for i, chunk in enumerate(chunks, start=1):
        pages = ", ".join(str(p) for p in chunk.page_numbers)
        print(f"  [{i}] {chunk.source_document}  p.{pages}  score={chunk.score:.3f}")


if __name__ == "__main__":
    main()
