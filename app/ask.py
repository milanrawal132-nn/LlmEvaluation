"""LLMEvalIQ — live Q&A frontend.

Launch:
    streamlit run app/ask.py

Type a question, it retrieves from the indexed corpus and generates an
answer — the SAME retrieve() + generate() functions every evaluation phase
used, so an answer here is exactly what the pipeline would have produced if
this question had been in the gold set. You can also upload your own PDF:
it gets embedded automatically into a separate index, and you can then ask
questions about it specifically.

Kept deliberately SEPARATE from app/dashboard.py: the dashboard is a
portfolio artefact that must never call an API, even by accident. This file
is the opposite — it exists ONLY to call the API, on demand, when a
question is submitted or a document is uploaded. Needs OPENAI_API_KEY and a
built index.
"""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_DIR = PROJECT_ROOT / "data" / "chroma"

# Uploaded documents get their OWN index, never merged into the curated
# corpus — build_index() always builds a fresh collection (see
# src/ingestion.py), so pointing an upload at STORE_DIR would silently wipe
# the 12-document corpus. A separate store_dir makes that impossible.
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_STORE_DIR = PROJECT_ROOT / "data" / "chroma_uploads"

# The accepted configuration, per the Phase 7A pre-registered selection rule
# and Phase 7B robustness check. Shown to the user, not silently assumed.
ACCEPTED_CHUNK_SIZE = 600
ACCEPTED_OVERLAP = 50


def load_env() -> bool:
    """Load OPENAI_API_KEY from .env. Returns whether a key ended up set —
    the caller decides what to do about it, this function never raises."""
    import os

    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    return bool(os.getenv("OPENAI_API_KEY"))


def index_ready() -> bool:
    return STORE_DIR.exists()


def file_signature(file_bytes: bytes, filename: str) -> str:
    """Identify an upload by content, not just filename — re-selecting the
    same file (or Streamlit re-running the script) must not re-trigger a
    real embedding API call for work already done this session."""
    return f"{filename}:{hashlib.sha256(file_bytes).hexdigest()[:16]}"


def index_uploaded_pdf(
    file_bytes: bytes,
    filename: str,
    uploads_dir: Path = UPLOADS_DIR,
    store_dir: Path = UPLOAD_STORE_DIR,
    chunk_size: int = ACCEPTED_CHUNK_SIZE,
    overlap: int = ACCEPTED_OVERLAP,
) -> int:
    """Save an uploaded PDF and build a standalone index containing ONLY it.

    Reuses build_index() unchanged — the same embedding pipeline every
    evaluation phase used, applied to one new file instead of the curated
    12-document corpus. Returns the chunk count.

    `only=[filename]` matters even though uploads_dir usually holds one
    file: if an earlier upload's PDF is still sitting in uploads_dir, this
    guarantees today's embedding call covers only the file just uploaded.
    """
    from src.ingestion import build_index

    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / filename).write_bytes(file_bytes)

    return build_index(
        documents_dir=uploads_dir,
        store_dir=store_dir,
        only=[filename],
        chunk_size=chunk_size,
        overlap=overlap,
        show_progress=False,
    )


def render_upload_section(st) -> None:
    """Upload -> auto-embed -> ready. Runs the ONE build_index() call per
    distinct file, tracked via file_signature() in session_state so
    Streamlit's rerun-the-whole-script-on-every-interaction model can't
    accidentally re-embed the same file twice."""
    st.markdown("### Upload your own document")
    st.caption(
        "Embedded into its own index, separate from the 12-document corpus — "
        "uploading never modifies or replaces the main corpus."
    )

    uploaded = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded is None:
        if st.session_state.get("upload_signature"):
            st.success(
                f"✅ Ready — **{st.session_state['upload_filename']}** "
                f"({st.session_state['upload_chunk_count']} chunks indexed). "
                "Ask about it below."
            )
        return

    file_bytes = uploaded.getvalue()
    signature = file_signature(file_bytes, uploaded.name)

    if st.session_state.get("upload_signature") == signature:
        st.success(
            f"✅ Ready — **{st.session_state['upload_filename']}** "
            f"({st.session_state['upload_chunk_count']} chunks indexed). "
            "Ask about it below."
        )
        return

    with st.spinner(f"Embedding {uploaded.name}… this calls the OpenAI API."):
        try:
            chunk_count = index_uploaded_pdf(file_bytes, uploaded.name)
        except Exception as exc:  # noqa: BLE001 — surface, don't crash the page
            st.error(f"Could not index {uploaded.name}: {exc}")
            return

    st.session_state["upload_signature"] = signature
    st.session_state["upload_filename"] = uploaded.name
    st.session_state["upload_chunk_count"] = chunk_count
    st.success(f"✅ Ready — **{uploaded.name}** ({chunk_count} chunks indexed). Ask about it below.")


def render_question_mode(st, store_dir: Path) -> None:
    """Top-K retrieval + generation — for a specific, answerable-from-one-
    passage question. NOT the right tool for whole-document requests; see
    render_whole_document_tool() for those."""
    question = st.text_input(
        "Your question",
        placeholder="e.g. How many board meetings did Ecoplast hold during 2025-26?",
    )
    ask_clicked = st.button("Ask", type="primary", disabled=not question.strip())

    if not ask_clicked:
        st.info(
            "The system prompt instructs the model to say \"I don't know\" rather "
            "than guess when the retrieved context doesn't contain the answer — "
            "that is expected, correct behaviour, not a bug. This project's own "
            "evaluation found honest abstention on ~50-60% of its gold questions.",
            icon="ℹ️",
        )
        return

    from src.generation import answer_question
    from src.retrieval import TOP_K

    started = time.perf_counter()
    with st.spinner("Retrieving and generating…"):
        try:
            answer, chunks = answer_question(question, store_dir, k=TOP_K)
        except Exception as exc:  # noqa: BLE001 — surface any API/index error to the user, don't crash the page
            st.error(f"Something went wrong: {exc}")
            return
    elapsed = time.perf_counter() - started

    st.markdown("### Answer")
    st.write(answer.text)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input tokens", answer.input_tokens)
    c2.metric("Output tokens", answer.output_tokens)
    c3.metric("Cost", f"${answer.cost_usd():.6f}")
    c4.metric("Latency", f"{elapsed:.2f}s")

    st.markdown(f"### Retrieved context (top-{TOP_K})")
    st.caption(
        "This is exactly what the model saw — nothing else. If the answer looks "
        "wrong, check here first: was the right passage even retrieved?"
    )
    for i, chunk in enumerate(chunks, start=1):
        pages = ", ".join(str(p) for p in chunk.page_numbers)
        with st.expander(f"[{i}] {chunk.source_document} — p.{pages} — score {chunk.score:.3f}"):
            st.text(chunk.text)


def render_document_output(st, output, label: str) -> None:
    st.markdown(f"### {label}")
    st.write(output.text)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input tokens", output.input_tokens)
    c2.metric("Output tokens", output.output_tokens)
    c3.metric("Cost", f"${output.cost_usd():.6f}")
    c4.metric("Latency", f"{output.latency_seconds:.2f}s")
    if output.call_count > 1:
        st.caption(
            f"Document needed {output.call_count} API calls (map-reduce: "
            f"summarized in sections, then combined) — it didn't fit in one call."
        )


def render_whole_document_tool(st, tool_name: str, generator) -> None:
    """Shared UI for Summary/Notes: an explicit button (this costs real API
    calls and reads the WHOLE document — never auto-triggered), with the
    result cached in session_state per upload so it survives reruns (e.g.
    switching modes) until you deliberately regenerate it."""
    cache_key = f"{tool_name.lower()}_{st.session_state['upload_signature']}"
    button_label = f"Regenerate {tool_name}" if cache_key in st.session_state else f"Generate {tool_name}"

    if st.button(button_label):
        pdf_path = UPLOADS_DIR / st.session_state["upload_filename"]
        with st.spinner(f"Reading the whole document and generating {tool_name.lower()}…"):
            try:
                st.session_state[cache_key] = generator(pdf_path)
            except Exception as exc:  # noqa: BLE001 — surface, don't crash the page
                st.error(f"Could not generate {tool_name.lower()}: {exc}")
                return

    if cache_key in st.session_state:
        render_document_output(st, st.session_state[cache_key], tool_name)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="LLMEvalIQ — Ask", page_icon="💬", layout="centered")
    st.title("💬 Ask the corpus")
    st.caption(
        "Live retrieval + generation at the accepted configuration "
        f"(chunk_size={ACCEPTED_CHUNK_SIZE}, overlap={ACCEPTED_OVERLAP}, TOP_K=5). "
        "Every question, upload, summary, and notes request here calls the OpenAI "
        "API — this page is NOT the offline portfolio dashboard (see "
        "app/dashboard.py for that)."
    )

    has_key = load_env()
    if not has_key:
        st.error(
            "No `OPENAI_API_KEY` found. Copy `.env.example` to `.env` and add "
            "your key, then restart this page."
        )
        st.stop()

    render_upload_section(st)
    st.divider()

    corpus_available = index_ready()
    upload_available = bool(st.session_state.get("upload_signature"))

    if not corpus_available and not upload_available:
        st.error(
            f"No corpus index found at `{STORE_DIR}`, and nothing uploaded yet. "
            f"Either upload a PDF above, or build the main index:\n\n"
            f"```bash\n./.venv/bin/python -u scripts/build_index.py "
            f"--chunk-size {ACCEPTED_CHUNK_SIZE} --overlap {ACCEPTED_OVERLAP}\n```"
        )
        st.stop()

    source_options = []
    if corpus_available:
        source_options.append("The 12-document corpus")
    if upload_available:
        source_options.append(f"My upload — {st.session_state['upload_filename']}")
    source = st.radio("Ask about", source_options, horizontal=True) if len(source_options) > 1 else source_options[0]
    store_dir = UPLOAD_STORE_DIR if source.startswith("My upload") else STORE_DIR
    is_upload = source.startswith("My upload")

    if source == "The 12-document corpus":
        with st.expander("Which companies can I ask about?"):
            st.write(
                "Alivus, Alu Wind, Ecoplast, Ganesh, Goa Carbon, Infosys, Mahindra, "
                "Reliance, Rishiroop, Sayaji, Sumit, Tata Motors — FY2024-25 or "
                "FY2025-26 annual reports, depending on the company."
            )

    # Summary/Notes only make sense for ONE document read in full. The
    # 12-document corpus (3,129 pages) has no single "whole document" to
    # read — that is a different, much bigger problem this tool does not
    # attempt to solve, so the option is not offered for it at all.
    mode_options = ["Ask a question"]
    if is_upload:
        mode_options += ["Summary", "Notes"]
    mode = st.radio("Mode", mode_options, horizontal=True) if len(mode_options) > 1 else mode_options[0]
    if is_upload and mode != "Ask a question":
        st.caption(
            "Reads the WHOLE uploaded document (not top-K retrieval) — the right "
            "tool for a request that isn't about one specific passage."
        )

    if mode == "Ask a question":
        render_question_mode(st, store_dir)
    elif mode == "Summary":
        from app.document_tools import summarize_document

        render_whole_document_tool(st, "Summary", summarize_document)
    elif mode == "Notes":
        from app.document_tools import generate_notes

        render_whole_document_tool(st, "Notes", generate_notes)


if __name__ == "__main__":
    main()
