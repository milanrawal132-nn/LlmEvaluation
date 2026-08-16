"""Whole-document tools for an uploaded PDF: summary and study notes.

Deliberately SEPARATE from src/generation.py's answer_question(). That
function is tuned for retrieval-augmented FACT lookup: a small top-K slice
of the document, and a prompt that refuses to go beyond what was retrieved.
Summarizing or making notes needs the opposite shape — the WHOLE document,
and a prompt that is explicitly allowed to synthesize across all of it.

For documents that don't fit comfortably in one call, this map-reduces:
summarize fixed-size slices independently, then combine those partial
summaries into one coherent final pass. Every call's tokens are added up so
the reported cost is the true total, not just the final call's.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

MODEL = "gpt-4o-mini"  # same generation model as the rest of the project

# Same verified pricing as Phase 9 (checked 2026-08-15 against OpenAI's
# pricing page). Re-verify before trusting this for a cost figure much later.
INPUT_COST_PER_MTOK = 0.15
OUTPUT_COST_PER_MTOK = 0.60

# Conservative — well under gpt-4o-mini's 128K-token context window, leaving
# room for the prompt instructions and the output. Documents under this are
# sent whole, in one call; larger ones are map-reduced.
DIRECT_CHAR_LIMIT = 60_000
MAP_CHUNK_CHARS = 12_000

SUMMARY_SYSTEM_PROMPT = """You summarize documents clearly and concisely.

Produce a well-organized summary covering the main topics, key points, and
conclusions. Use the document's own terminology. Do not add outside
information that is not present in the document."""

NOTES_SYSTEM_PROMPT = """You produce structured study notes from a document,
in the style a student would use to revise.

Use headings for major sections/topics, bullet points for key facts,
definitions, and concepts, and clearly flag important terms, formulas, or
numbers. Be thorough but concise. Do not add outside information that is
not present in the document."""

PARTIAL_SYSTEM_PROMPT = """You are given ONE EXCERPT from a larger document,
not the whole thing. Summarize this excerpt in 4-8 concise bullet points,
covering only what is actually in this excerpt. Do not speculate about
content you have not seen."""


@dataclass
class DocumentOutput:
    """A generated summary or notes document, plus what Phase 9's cost
    discipline requires: exact token counts and elapsed time."""

    text: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    call_count: int  # >1 means map-reduce was used

    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * INPUT_COST_PER_MTOK
            + self.output_tokens / 1_000_000 * OUTPUT_COST_PER_MTOK
        )


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set — copy .env.example to .env")
    return OpenAI(api_key=key)


def full_document_text(pdf_path: Path) -> str:
    """The whole document as one string — the input a summary/notes call
    actually needs, unlike answer_question()'s top-K chunk slice."""
    from src.ingestion import load_pdf_pages, source_text

    return source_text(load_pdf_pages(pdf_path))


def _chat(client: OpenAI, system_prompt: str, user_content: str) -> tuple[str, int, int]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    return text, response.usage.prompt_tokens, response.usage.completion_tokens


def _split_into_map_chunks(text: str, chunk_chars: int = MAP_CHUNK_CHARS) -> list[str]:
    """Fixed-size slices for the map step. No overlap needed here — unlike
    retrieval chunking, we are not trying to preserve a searchable boundary,
    every slice gets summarized and nothing is scored against the others."""
    return [text[i:i + chunk_chars] for i in range(0, len(text), chunk_chars)] or [""]


def _generate(text: str, final_system_prompt: str, combine_label: str) -> DocumentOutput:
    """Direct single call if the document fits; map-reduce otherwise."""
    started = time.perf_counter()
    client = _client()
    total_input = total_output = 0
    call_count = 0

    if len(text) <= DIRECT_CHAR_LIMIT:
        result, in_tok, out_tok = _chat(client, final_system_prompt, text)
        total_input += in_tok
        total_output += out_tok
        call_count += 1
    else:
        partials = []
        # Pass MAP_CHUNK_CHARS explicitly rather than relying on
        # _split_into_map_chunks' own default: a default argument is bound
        # once at function-definition time, so it would silently ignore any
        # later change to the module-level constant.
        for chunk in _split_into_map_chunks(text, chunk_chars=MAP_CHUNK_CHARS):
            partial, in_tok, out_tok = _chat(client, PARTIAL_SYSTEM_PROMPT, chunk)
            partials.append(partial)
            total_input += in_tok
            total_output += out_tok
            call_count += 1

        combined_input = "\n\n".join(f"[Section {i + 1}]\n{p}" for i, p in enumerate(partials))
        prompt = (
            f"Below are section-by-section notes covering the full document, "
            f"in order. Combine them into one coherent {combine_label}:\n\n{combined_input}"
        )
        result, in_tok, out_tok = _chat(client, final_system_prompt, prompt)
        total_input += in_tok
        total_output += out_tok
        call_count += 1

    elapsed = time.perf_counter() - started
    return DocumentOutput(result, total_input, total_output, elapsed, call_count)


def summarize_document(pdf_path: Path) -> DocumentOutput:
    return _generate(full_document_text(pdf_path), SUMMARY_SYSTEM_PROMPT, "summary")


def generate_notes(pdf_path: Path) -> DocumentOutput:
    return _generate(full_document_text(pdf_path), NOTES_SYSTEM_PROMPT, "set of study notes")
