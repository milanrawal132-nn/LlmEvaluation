"""Turn PDF files into searchable chunks in a vector store.

This is the OFFLINE half of the RAG pipeline (Phase 0, part A):

    documents -> text -> chunks -> embeddings -> vector store

Everything here runs once, ahead of any user question.
"""

import os
import time
from dataclasses import dataclass
from pathlib import Path

import chromadb
from openai import OpenAI
from pypdf import PdfReader

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

# One API call per batch instead of one per chunk. With ~23,000 chunks that is
# the difference between ~230 requests and 23,000.
EMBED_BATCH_SIZE = 128

# Chroma's own server-side cap on a single collection.add() call is ~5,461
# (observed; not a project choice). This must be enforced separately from
# EMBED_BATCH_SIZE — that constant only bounds the embedding API calls, not
# how many rows one Chroma write can carry. Kept comfortably under the
# observed cap rather than pinned exactly to it.
ADD_BATCH_SIZE = 5000

COLLECTION_NAME = "llmevaliq"


@dataclass
class Chunk:
    """One indexed piece of a document, with the provenance evaluation needs.

    page_numbers is not decoration. Our corpus contains a 590-page report;
    without page provenance a failed question is unresearchable, and
    Evidence Coverage@K has nothing to anchor to.

    start_char / end_char are the chunk's character range in the document's
    SOURCE TEXT — the "\\n".join of the extracted pages, built in
    split_into_chunks(). That string depends only on the PDF, never on
    chunk_size or overlap, which is the whole point: it gives every
    configuration one shared coordinate system.

    Text-substring evidence matching cannot do that. A snippet is either
    inside a chunk or it is not, and which one flips with chunk size — so the
    ruler changes shape with the thing it measures. Offsets do not move.
    """

    text: str
    source_document: str
    chunk_index: int
    page_numbers: list[int]
    start_char: int
    end_char: int


def load_pdf_pages(path: Path) -> list[str]:
    """Extract text from a PDF, one string PER PAGE.

    Returns pages rather than one blob so chunking can record which pages each
    chunk came from. Merging to a single string first destroys that mapping
    irreversibly.

    Image-only pages yield "" rather than raising — `or ""` guards the None
    that pypdf returns for pages it cannot read.
    """
    reader = PdfReader(path)
    return [page.extract_text() or "" for page in reader.pages]


def split_into_chunks(
    pages: list[str],
    source_document: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Cut a document into overlapping pieces, tracking page provenance.

    The trick for keeping page numbers: join the pages into one string, but
    first record the character offset at which each page starts. A chunk is a
    character range, so any page whose range overlaps the chunk's range
    contributed text to it.

        page_starts = [0, 3200, 6100, ...]
        chunk spans chars 3050..3550  ->  overlaps page 1 and page 2

    Why overlap at all: a hard cut can slice a sentence — and therefore a fact
    — in half. Overlap gives every sentence a chance to survive intact inside
    at least one chunk. The cost is more chunks: we advance by
    (chunk_size - overlap), not chunk_size.
    """
    page_starts: list[int] = []
    parts: list[str] = []
    cursor = 0
    for page_text in pages:
        page_starts.append(cursor)
        parts.append(page_text)
        cursor += len(page_text) + 1  # +1 for the "\n" join below

    full_text = source_text(parts)

    def pages_for(start: int, end: int) -> list[int]:
        """Every 1-based page number whose character range overlaps [start,end)."""
        found = []
        for i, page_start in enumerate(page_starts):
            page_end = page_start + len(pages[i])
            if page_start < end and start < page_end:
                found.append(i + 1)
        return found or [1]

    stride = chunk_size - overlap
    if stride <= 0:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    for start in range(0, len(full_text), stride):
        text = full_text[start : start + chunk_size]
        if not text.strip():          # skip runs of blank pages
            continue
        chunks.append(
            Chunk(
                text=text,
                source_document=source_document,
                chunk_index=len(chunks),
                page_numbers=pages_for(start, start + len(text)),
                # Offsets into full_text, which is chunk-size independent.
                # len(text), not chunk_size — the last chunk is short.
                start_char=start,
                end_char=start + len(text),
            )
        )
    return chunks


def source_text(pages: list[str]) -> str:
    """The canonical character coordinate system for one document.

    This MUST stay byte-identical to what split_into_chunks() slices, or gold
    offsets and chunk offsets would be measured against different rulers and
    every span metric would be quietly wrong. Kept as one function, called by
    both, precisely so the two cannot drift apart.
    """
    return "\n".join(pages)


def _client() -> OpenAI:
    """One OpenAI client, reading OPENAI_API_KEY from the environment."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set — copy .env.example to .env")
    return OpenAI(api_key=key)


def embed_texts(texts: list[str], show_progress: bool = False) -> list[list[float]]:
    """Turn strings into vectors, in batches.

    Batching matters: the per-request overhead dominates at this scale, so
    sending 128 chunks per call is roughly two orders of magnitude faster than
    one call per chunk — for identical token cost.
    """
    client = _client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # The API may return items out of order; `index` is authoritative.
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
        if show_progress:
            print(f"  embedded {min(start + EMBED_BATCH_SIZE, len(texts)):>6} / {len(texts)}")
    return vectors


def build_index(
    documents_dir: Path,
    store_dir: Path,
    only: list[str] | None = None,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    show_progress: bool = True,
) -> int:
    """Run the whole offline pipeline: load -> split -> embed -> store.

    Args:
        documents_dir: Folder of source PDFs.
        store_dir: Where the vector store persists to disk.
        only: Optional filenames to index. Default indexes every PDF.
        chunk_size / overlap: Phase 7 varies these.
        show_progress: Print per-document progress.

    Returns:
        How many chunks were indexed.
    """
    paths = sorted(documents_dir.glob("*.pdf"))
    if only:
        wanted = set(only)
        paths = [p for p in paths if p.name in wanted]
    if not paths:
        raise FileNotFoundError(f"No matching PDFs in {documents_dir}")

    # A fresh collection every build. Re-indexing on top of an old one would
    # silently mix chunk sizes, which would quietly invalidate Phase 7.
    store_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(store_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity, not L2
    )

    total = 0
    started = time.time()
    for path in paths:
        pages = load_pdf_pages(path)
        chunks = split_into_chunks(pages, path.name, chunk_size, overlap)
        if show_progress:
            print(f"{path.name}: {len(pages)} pages -> {len(chunks)} chunks")

        vectors = embed_texts([c.text for c in chunks])

        # Chroma metadata values must be scalars, so the page list is stored
        # as a comma-joined string and parsed back in retrieval.py.
        ids = [f"{path.name}::{c.chunk_index}" for c in chunks]
        metadatas = [
            {
                "source_document": c.source_document,
                "chunk_index": c.chunk_index,
                "pages": ",".join(str(p) for p in c.page_numbers),
                # Chunk-size-independent coordinates, for Phase 7A's
                # cross-configuration span metrics.
                "start_char": c.start_char,
                "end_char": c.end_char,
            }
            for c in chunks
        ]
        documents = [c.text for c in chunks]

        # collection.add() has its own server-side cap (independent of
        # EMBED_BATCH_SIZE, which only bounds the embedding API calls above).
        # A single document can exceed it — at chunk_size=300 our largest
        # report cuts into 7,038 chunks against Chroma's ~5,461 write cap —
        # so the WRITE also has to be batched, not just the embedding.
        for start in range(0, len(chunks), ADD_BATCH_SIZE):
            end = start + ADD_BATCH_SIZE
            collection.add(
                ids=ids[start:end],
                embeddings=vectors[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
        total += len(chunks)

    if show_progress:
        print(f"\nindexed {total:,} chunks in {time.time() - started:.1f}s")
    return total
