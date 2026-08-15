"""Find the chunks most likely to contain the answer.

This is the librarian. It runs on every question:

    question -> embed -> similarity search -> top K chunks
"""

from dataclasses import dataclass
from pathlib import Path

import chromadb

# Imported, never redeclared. The question must be embedded with the exact
# model the documents were embedded with — this import is what guarantees it.
from src.ingestion import COLLECTION_NAME, embed_texts

# How many chunks we hand to the LLM. Phase 5 measures Recall@1/3/5/10 to
# show what this number actually buys us.
TOP_K = 5


@dataclass
class RetrievedChunk:
    """One chunk the search returned, plus enough provenance to grade it.

    Provenance is graded at three resolutions in Phase 5:

      source_document -> Document Recall@K.   Generous. On a 590-page report
                         ~4,100 chunks share this value, so almost any hit counts.

      text            -> Any Evidence@K and Evidence Coverage@K. We check
                         whether this chunk CONTAINS each required gold snippet.
                         Coverage is the honest number.

      page_numbers    -> human debugging. When a question fails you want to
                         open the PDF at the right page, not scroll 590 of them.

      start/end_char  -> Gold Span metrics (Phase 7A). Character offsets into
                         the document's source text, which does not move when
                         chunk_size changes. This is the ONLY provenance here
                         that is comparable ACROSS configurations.

    start_char/end_char are None for indexes built before Phase 7A. The span
    metrics raise rather than guess, so a stale index fails loudly instead of
    silently scoring zero.
    """

    text: str
    source_document: str
    chunk_index: int
    page_numbers: list[int]
    score: float
    start_char: int | None = None
    end_char: int | None = None


def retrieve(question: str, store_dir: Path, k: int = TOP_K) -> list[RetrievedChunk]:
    """Return the k chunks closest in meaning to the question.

    Closest "in meaning", not in wording — that is the whole point of
    embeddings. "What did Goa Carbon earn?" should match "sales and other
    income was ₹70,879.78 lakhs" despite sharing almost no words.

    Note the question goes through embed_texts() — the SAME function the
    documents went through. That is not a stylistic choice: querying a cosine
    space with vectors from a different model returns confident nonsense.
    """
    client = chromadb.PersistentClient(path=str(store_dir))
    collection = client.get_collection(COLLECTION_NAME)

    query_vector = embed_texts([question])[0]
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns one list per query; we sent one query, so index [0].
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    chunks: list[RetrievedChunk] = []
    for text, meta, distance in zip(documents, metadatas, distances):
        pages = [int(p) for p in str(meta.get("pages", "")).split(",") if p]
        # .get(), not [...]: indexes built before Phase 7A have no offsets.
        start_char = meta.get("start_char")
        end_char = meta.get("end_char")
        chunks.append(
            RetrievedChunk(
                text=text,
                source_document=str(meta["source_document"]),
                chunk_index=int(meta["chunk_index"]),
                page_numbers=pages,
                start_char=None if start_char is None else int(start_char),
                end_char=None if end_char is None else int(end_char),
                # Collection uses cosine DISTANCE; similarity is 1 - distance,
                # so a score near 1.0 means near-identical meaning.
                score=1.0 - float(distance),
            )
        )
    return chunks
