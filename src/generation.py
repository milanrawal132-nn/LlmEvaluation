"""Turn retrieved chunks + a question into an answer.

This is the student in the open-book exam. The LLM is NOT the knowledge
source here — it is a reading-comprehension engine over text we hand it.

Implemented in Phase 4, measured in Phases 6 and 9.
"""

from dataclasses import dataclass

from src.retrieval import RetrievedChunk

# One LLM for the whole project (roadmap rule: change one thing at a time).
# gpt-4o-mini is cheap enough to run the full 100-question set many times
# while we iterate. Swap it here and nowhere else if you want a bigger model.
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
    Being able to see what the model actually received is most of debugging.
    """
    raise NotImplementedError("Phase 4")


def generate(question: str, chunks: list[RetrievedChunk]) -> Answer:
    """Ask the LLM the question, given only these chunks as context.

    Args:
        question: The user's question.
        chunks: Context from retrieval.

    Returns:
        The answer, with token counts and wall-clock latency attached.
    """
    raise NotImplementedError("Phase 4")
