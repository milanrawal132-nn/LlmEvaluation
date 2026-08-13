"""Turn PDF files into searchable chunks in a vector store.

This is the OFFLINE half of the RAG pipeline (Phase 0, part A):

    documents -> text -> chunks -> embeddings -> vector store

Everything here runs once, ahead of any user question.
Implemented in Phase 4.
"""

from pathlib import Path

# The two parameters that define a "configuration" in this project.
# Phase 7 changes CHUNK_SIZE (300 / 600 / 1000) and nothing else — that is
# what makes it a controlled experiment.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Query and documents MUST use this same model. Two different embedding models
# produce two incompatible coordinate systems and retrieval silently returns junk.
# retrieval.py imports this constant rather than redeclaring it, so the two
# sides physically cannot drift apart.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # length of each vector this model returns

# Embeddings cost money too, but only once per document (not per question).
# Phase 9 reports this separately from per-answer cost for exactly that reason.
# Verify at https://platform.openai.com/docs/pricing
EMBEDDING_COST_PER_MTOK = 0.02


def load_pdf(path: Path) -> str:
    """Extract all text from one PDF.

    Args:
        path: Path to a .pdf file.

    Returns:
        The document's full text as a single string.
    """
    raise NotImplementedError("Phase 4")


def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Cut a long document into overlapping pieces.

    Why chunk at all: a 300-page report does not fit in a prompt, and stuffing
    everything in is slower, pricier, and LESS accurate than sending 5 good pieces.

    Why overlap: a hard cut can slice a sentence — and therefore a fact — in half.
    Overlap gives every sentence a chance to survive intact inside some chunk.

    Args:
        text: Full document text.
        chunk_size: Target characters per chunk.
        overlap: Characters each chunk repeats from the previous one.

    Returns:
        The chunks, in document order.
    """
    raise NotImplementedError("Phase 4")


def build_index(documents_dir: Path, store_dir: Path) -> int:
    """Run the whole offline pipeline: load -> split -> embed -> store.

    Args:
        documents_dir: Folder of source PDFs.
        store_dir: Where the vector store persists to disk.

    Returns:
        How many chunks were indexed.
    """
    raise NotImplementedError("Phase 4")
