"""Tests for the offline half of the pipeline.

The embedding-order tests exist because that failure is invisible. If the
OpenAI API returns a batch out of order and we zip it naively to our inputs,
every vector is attached to the wrong chunk. Nothing raises. The index simply
returns confident nonsense forever, and it looks like a model quality problem.
"""

import pytest

from src import ingestion
from src.ingestion import Chunk, embed_texts, split_into_chunks


# --------------------------------------------------------------------------
# Fakes: stand in for the OpenAI client so tests need no API key and no network
# --------------------------------------------------------------------------
class _FakeItem:
    """Mimics one element of response.data — carries its own `index`."""

    def __init__(self, index: int, embedding: list[float]) -> None:
        self.index = index
        self.embedding = embedding


class _FakeResponse:
    def __init__(self, data: list[_FakeItem]) -> None:
        self.data = data


class _ShuffledEmbeddings:
    """Returns each batch in REVERSE order, exactly as a real API is permitted to."""

    def create(self, model: str, input: list[str]):
        # Embedding for text "tN" is [N]. Reversed so position != index.
        items = [_FakeItem(i, [float(text[1:])]) for i, text in enumerate(input)]
        return _FakeResponse(list(reversed(items)))


class _FakeClient:
    embeddings = _ShuffledEmbeddings()


@pytest.fixture
def shuffled_client(monkeypatch):
    monkeypatch.setattr(ingestion, "_client", lambda: _FakeClient())


# --------------------------------------------------------------------------
# Embedding order
# --------------------------------------------------------------------------
def test_embeddings_realigned_when_api_returns_out_of_order(shuffled_client):
    """Vectors must come back matched to their INPUT position, not response position."""
    texts = ["t0", "t1", "t2", "t3"]

    vectors = embed_texts(texts)

    # Each text "tN" embeds to [N]; correct alignment means vectors[i] == [i].
    assert vectors == [[0.0], [1.0], [2.0], [3.0]], (
        "embeddings were not realigned to input order — every chunk in the "
        "index would carry another chunk's vector"
    )


def test_embeddings_realigned_across_batch_boundaries(shuffled_client, monkeypatch):
    """Realignment must hold per batch, not just for a single request."""
    monkeypatch.setattr(ingestion, "EMBED_BATCH_SIZE", 2)
    texts = [f"t{i}" for i in range(5)]        # 3 batches: [0,1] [2,3] [4]

    vectors = embed_texts(texts)

    assert vectors == [[0.0], [1.0], [2.0], [3.0], [4.0]]
    assert len(vectors) == len(texts)


def test_embed_texts_returns_one_vector_per_input(shuffled_client):
    """A dropped or duplicated vector silently shifts every later chunk."""
    texts = [f"t{i}" for i in range(7)]
    assert len(embed_texts(texts)) == 7


# --------------------------------------------------------------------------
# Chunking and page provenance
# --------------------------------------------------------------------------
def test_chunk_overlap_is_exact():
    """Consecutive chunks must share exactly `overlap` characters."""
    chunks = split_into_chunks(["x" * 2000], "d.pdf", chunk_size=500, overlap=50)
    assert chunks[0].text[-50:] == chunks[1].text[:50]


def test_chunk_spanning_a_page_break_records_both_pages():
    """A fact split across a page boundary must remain locatable."""
    chunks = split_into_chunks(["a" * 1000, "b" * 1000], "d.pdf", chunk_size=500, overlap=50)
    spanning = [c for c in chunks if len(c.page_numbers) > 1]
    assert spanning, "no chunk recorded a page span"
    assert spanning[0].page_numbers == [1, 2]


def test_page_numbers_are_one_based_and_sorted():
    chunks = split_into_chunks(["a" * 600, "b" * 600, "c" * 600], "d.pdf")
    for chunk in chunks:
        assert chunk.page_numbers == sorted(chunk.page_numbers)
        assert min(chunk.page_numbers) >= 1


def test_blank_pages_do_not_produce_empty_chunks():
    chunks = split_into_chunks(["", "", "real content here"], "d.pdf", chunk_size=500, overlap=50)
    assert all(c.text.strip() for c in chunks)


def test_overlap_must_be_smaller_than_chunk_size():
    """A stride of zero would loop forever — fail loudly instead."""
    with pytest.raises(ValueError):
        split_into_chunks(["text"], "d.pdf", chunk_size=100, overlap=100)


def test_chunk_index_is_contiguous():
    """chunk_index is a join key into Chroma ids; gaps would break provenance."""
    chunks = split_into_chunks(["z" * 3000], "d.pdf")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(isinstance(c, Chunk) for c in chunks)


# --------------------------------------------------------------------------
# collection.add() batching
# --------------------------------------------------------------------------
# Regression test for a real Phase 7A failure: at chunk_size=300 our largest
# report cuts into 7,038 chunks, and Chroma's collection.add() has its own
# server-side row cap (~5,461) independent of EMBED_BATCH_SIZE, which only
# bounds the embedding API calls. A single unbatched add() call crashed the
# build; nothing about chunk_size, overlap, or content was wrong.
class _FakeCollection:
    """Records every add() call so a test can inspect batch sizes after the fact."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def add(self, ids, embeddings, documents, metadatas) -> None:
        assert len({len(ids), len(embeddings), len(documents), len(metadatas)}) == 1, (
            "a single add() call had mismatched list lengths"
        )
        self.calls.append(list(ids))


class _FakeChromaClient:
    def __init__(self) -> None:
        self.collection = _FakeCollection()

    def delete_collection(self, _name) -> None:
        pass

    def create_collection(self, _name, metadata=None) -> _FakeCollection:
        return self.collection


class _ConstantEmbeddings:
    """Any input, same-length vector — this test only cares about batch sizes."""

    def create(self, model: str, input: list[str]):
        return _FakeResponse([_FakeItem(i, [0.0]) for i, _ in enumerate(input)])


def test_build_index_batches_collection_add_under_the_chroma_cap(monkeypatch, tmp_path):
    """A document with more chunks than ADD_BATCH_SIZE must still index fully,
    in more than one add() call, with every original id preserved exactly once."""
    monkeypatch.setattr(ingestion, "ADD_BATCH_SIZE", 10)
    monkeypatch.setattr(ingestion, "_client", lambda: type(
        "_C", (), {"embeddings": _ConstantEmbeddings()}
    )())

    fake_client = _FakeChromaClient()
    monkeypatch.setattr(ingestion.chromadb, "PersistentClient", lambda path: fake_client)

    documents_dir = tmp_path / "docs"
    documents_dir.mkdir()
    monkeypatch.setattr(ingestion, "load_pdf_pages", lambda path: ["x" * 3000])

    # Any .pdf name works — load_pdf_pages is faked above, so no real PDF
    # parsing happens; only the filename is used, via glob().
    (documents_dir / "big.pdf").write_bytes(b"")

    total = ingestion.build_index(
        documents_dir=documents_dir,
        store_dir=tmp_path / "store",
        chunk_size=100,
        overlap=10,
        show_progress=False,
    )

    all_ids = [chunk_id for batch in fake_client.collection.calls for chunk_id in batch]
    assert len(all_ids) == total
    assert len(set(all_ids)) == total, "an id was written twice across batches"
    assert len(fake_client.collection.calls) > 1, "never actually exercised batching"
    assert all(len(batch) <= 10 for batch in fake_client.collection.calls)
