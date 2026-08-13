"""Find the chunks most likely to contain the answer.

This is the librarian. It runs on every question:

    question -> embed -> similarity search -> top K chunks

Implemented in Phase 4, measured in Phase 5.
"""

from dataclasses import dataclass
from pathlib import Path

# Imported, never redeclared. The question must be embedded with the exact
# model the documents were embedded with — this import is what guarantees it.
from src.ingestion import EMBEDDING_MODEL  # noqa: F401  (used in Phase 4)

# How many chunks we hand to the LLM. Phase 5 measures Recall@1/3/5/10 to
# show what this number actually buys us.
TOP_K = 5


@dataclass
class RetrievedChunk:
    """One chunk the search returned, plus why it was returned.

    We keep `source_document` because Phase 5 scores retrieval by comparing it
    against the `relevant_document` column of the gold questions.csv.
    We keep `score` because a low top score is an early warning that the
    question has no good answer in the corpus at all.
    """

    text: str
    source_document: str
    chunk_index: int
    score: float


def retrieve(question: str, store_dir: Path, k: int = TOP_K) -> list[RetrievedChunk]:
    """Return the k chunks closest in meaning to the question.

    Closest "in meaning", not in wording — that is the whole point of
    embeddings. "What was revenue?" should match "Total sales were $4.2B"
    even though they share almost no words.

    Args:
        question: The user's question, in plain text.
        store_dir: Where the vector store was persisted by ingestion.
        k: How many chunks to return.

    Returns:
        Chunks ordered best-match first.
    """
    raise NotImplementedError("Phase 4")
