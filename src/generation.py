"""Turn retrieved chunks + a question into an answer.

This is the student in the open-book exam. The LLM is NOT the knowledge
source here — it is a reading-comprehension engine over text we hand it.
"""

import os
import time
from dataclasses import dataclass

from openai import OpenAI

from src.retrieval import RetrievedChunk

# One LLM for the whole project (roadmap rule: change one thing at a time).
MODEL = "gpt-4o-mini"

# Price per 1,000,000 tokens, in US dollars. Phase 9 turns token counts into
# money with these.
#
# !! VERIFY THESE before quoting a cost figure anywhere that matters:
# !! https://platform.openai.com/docs/pricing
# !! Prices change, and a stale constant makes every number in Phase 9 wrong.
INPUT_COST_PER_MTOK = 0.15
OUTPUT_COST_PER_MTOK = 0.60

# This instruction is our primary defense against hallucination.
# Phase 6's faithfulness metric measures whether it actually worked.
SYSTEM_PROMPT = """You answer questions using only the context provided.

Rules:
- Use ONLY the context below. Do not use outside knowledge.
- If the context does not contain the answer, reply exactly: "I don't know."
- Be concise and factual. Do not speculate."""


@dataclass
class Answer:
    """A generated answer plus everything Phase 9 needs to price it."""

    text: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float

    def cost_usd(self) -> float:
        """Dollar cost of this single answer."""
        return (
            self.input_tokens / 1_000_000 * INPUT_COST_PER_MTOK
            + self.output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK
        )


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Assemble the retrieved chunks and the question into one prompt.

    Kept separate from generate() so a notebook can print the exact prompt.
    Being able to see what the model actually received is most of debugging —
    if the answer is wrong, the first question is always "was the fact even
    in the prompt?"

    Each chunk is labelled with its source and pages. That label is for the
    reader, not the model: when you print the prompt you can see instantly
    whether retrieval brought the right pages.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        pages = ", ".join(str(p) for p in chunk.page_numbers)
        blocks.append(
            f"[{i}] source: {chunk.source_document} (page {pages})\n{chunk.text}"
        )
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def generate(question: str, chunks: list[RetrievedChunk]) -> Answer:
    """Ask the LLM the question, given only these chunks as context.

    Latency and token counts are captured here because this is the only place
    they exist. The API reports usage on the response; if we do not record it
    now, Phase 9 can never recover it.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set — copy .env.example to .env")
    client = OpenAI(api_key=key)

    prompt = build_prompt(question, chunks)

    started = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    latency = time.perf_counter() - started

    return Answer(
        text=(response.choices[0].message.content or "").strip(),
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        latency_seconds=latency,
    )


def answer_question(question: str, store_dir, k: int | None = None) -> tuple[Answer, list[RetrievedChunk]]:
    """Convenience wrapper: retrieve, then generate.

    Returns the chunks alongside the answer because every evaluation metric in
    Phase 5 and 6 needs them. An answer without its context is unscoreable.
    """
    from src.retrieval import TOP_K, retrieve

    chunks = retrieve(question, store_dir, k or TOP_K)
    return generate(question, chunks), chunks
