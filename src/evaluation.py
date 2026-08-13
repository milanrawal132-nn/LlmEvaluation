"""Judge the pipeline. This file never changes the answer — it only scores it.

That separation is the point of the whole project. Retrieval and generation
fail independently, so we measure them independently:

    Recall@K      did the librarian bring the right page?   (Phase 5)
    Correctness   does the answer match the reference?      (Phase 6)
    Faithfulness  is every claim backed by the chunks?      (Phase 6)
    Relevance     did it answer the question asked?         (Phase 6)

Latency and cost are measured in generation.py (they come free with the API
call); Phase 9 just tabulates them.
"""

from dataclasses import dataclass

from src.retrieval import RetrievedChunk


@dataclass
class Scores:
    """Every metric for one question. One row of the Phase 6 results table."""

    question_id: str
    retrieval_hit: bool  # was the gold document in the retrieved chunks?
    correctness: bool
    faithfulness: bool
    relevance: bool


def recall_at_k(
    retrieved: list[RetrievedChunk],
    relevant_document: str,
    k: int,
) -> bool:
    """Did the gold document appear in the top k retrieved chunks?

    Recall@K for a single question is binary: hit or miss. The headline
    "Recall@5 = 0.82" is the mean of these across all questions.

    Args:
        retrieved: Chunks from retrieval, best-match first.
        relevant_document: The gold answer's source, from questions.csv.
        k: Cutoff. Only the first k chunks are considered.

    Returns:
        True if any of the top k chunks came from the gold document.
    """
    raise NotImplementedError("Phase 5")


def judge_correctness(answer: str, reference_answer: str) -> bool:
    """Does the answer agree with the human-written reference answer?

    String comparison fails here — "$890 million" and "890M USD" are the same
    fact. So we use an LLM as the judge, with the reference answer in hand.
    """
    raise NotImplementedError("Phase 6")


def judge_faithfulness(answer: str, chunks: list[RetrievedChunk]) -> bool:
    """Is every claim in the answer supported by the retrieved chunks?

    This is the hallucination detector. Note it does NOT look at the reference
    answer: an answer can be factually right and still unfaithful, if the model
    pulled it from training data rather than from our documents.
    """
    raise NotImplementedError("Phase 6")


def judge_relevance(answer: str, question: str) -> bool:
    """Does the answer address the question that was actually asked?

    Catches the on-topic-but-wrong-question failure: asked for 2024 profit,
    answered with 2023 revenue.
    """
    raise NotImplementedError("Phase 6")
