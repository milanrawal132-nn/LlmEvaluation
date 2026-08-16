"""Tests for the live Q&A page (app/ask.py).

These must NEVER trigger a real API call — the page only calls the API
after the user clicks "Ask" or uploads a file, and AppTest.run() without
either action must render every guard state (missing key, missing index)
safely, and never touch retrieval/generation/build_index.
"""

import app.ask as ask_app


def test_index_ready_false_when_store_dir_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_app, "STORE_DIR", tmp_path / "does_not_exist")
    assert ask_app.index_ready() is False


def test_index_ready_true_when_store_dir_present(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_app, "STORE_DIR", tmp_path)
    assert ask_app.index_ready() is True


def test_load_env_returns_false_with_no_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(ask_app, "PROJECT_ROOT", tmp_path)  # no .env here
    assert ask_app.load_env() is False


def test_page_renders_with_no_exception_and_makes_no_api_call_by_default(monkeypatch):
    """The core safety property: loading the page (nothing clicked, nothing
    uploaded) must never reach generation/retrieval/indexing code at all."""
    called = {"hit": False}

    def _explode(*_args, **_kwargs):
        called["hit"] = True
        raise AssertionError("API call made with no button click and no upload")

    monkeypatch.setattr("src.generation.answer_question", _explode)
    monkeypatch.setattr("src.ingestion.build_index", _explode)
    monkeypatch.setattr("app.document_tools.summarize_document", _explode)
    monkeypatch.setattr("app.document_tools.generate_notes", _explode)

    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ask_app.__file__))
    at.run(timeout=30)

    assert not at.exception, [e.message for e in at.exception]
    assert called["hit"] is False


def test_ask_button_disabled_when_question_is_empty():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ask_app.__file__))
    at.run(timeout=30)
    buttons = [b for b in at.button if b.label == "Ask"]
    if buttons:  # only reachable past the key/index guards
        assert buttons[0].disabled is True


# ==========================================================================
# Upload signature — the guard against re-embedding the same file twice
# ==========================================================================
def test_file_signature_is_stable_for_identical_bytes():
    a = ask_app.file_signature(b"pdf-bytes-here", "report.pdf")
    b = ask_app.file_signature(b"pdf-bytes-here", "report.pdf")
    assert a == b


def test_file_signature_differs_for_different_content():
    a = ask_app.file_signature(b"version one", "report.pdf")
    b = ask_app.file_signature(b"version two", "report.pdf")
    assert a != b


def test_file_signature_differs_for_different_filenames_same_content():
    """Two different uploads that happen to share content should not collide
    and silently skip indexing the second file."""
    a = ask_app.file_signature(b"same bytes", "a.pdf")
    b = ask_app.file_signature(b"same bytes", "b.pdf")
    assert a != b


# ==========================================================================
# index_uploaded_pdf — file handling + correct build_index() call, no
# real embedding (build_index itself is mocked out here)
# ==========================================================================
def test_index_uploaded_pdf_writes_the_file_to_uploads_dir(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    store_dir = tmp_path / "store"
    monkeypatch.setattr("src.ingestion.build_index", lambda **kwargs: 42)

    count = ask_app.index_uploaded_pdf(
        b"%PDF-fake-bytes", "myfile.pdf", uploads_dir=uploads_dir, store_dir=store_dir
    )

    assert (uploads_dir / "myfile.pdf").read_bytes() == b"%PDF-fake-bytes"
    assert count == 42


def test_index_uploaded_pdf_restricts_build_to_only_the_uploaded_file(tmp_path, monkeypatch):
    """A stale file left over from a previous upload in the same uploads_dir
    must NOT get re-embedded alongside the new one."""
    uploads_dir = tmp_path / "uploads"
    store_dir = tmp_path / "store"
    uploads_dir.mkdir(parents=True)
    (uploads_dir / "old_upload.pdf").write_bytes(b"stale")

    captured = {}

    def fake_build_index(**kwargs):
        captured.update(kwargs)
        return 7

    monkeypatch.setattr("src.ingestion.build_index", fake_build_index)

    ask_app.index_uploaded_pdf(
        b"new bytes", "new_upload.pdf", uploads_dir=uploads_dir, store_dir=store_dir
    )

    assert captured["only"] == ["new_upload.pdf"]
    assert captured["documents_dir"] == uploads_dir
    assert captured["store_dir"] == store_dir


def test_index_uploaded_pdf_uses_the_accepted_configuration_by_default(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr("src.ingestion.build_index", lambda **kwargs: captured.update(kwargs) or 1)

    ask_app.index_uploaded_pdf(
        b"bytes", "f.pdf", uploads_dir=tmp_path / "u", store_dir=tmp_path / "s"
    )

    assert captured["chunk_size"] == ask_app.ACCEPTED_CHUNK_SIZE
    assert captured["overlap"] == ask_app.ACCEPTED_OVERLAP


def test_index_uploaded_pdf_never_shows_build_progress_output(tmp_path, monkeypatch):
    """show_progress=True would print to stdout in a Streamlit process —
    harmless but noisy; the upload path should suppress it."""
    captured = {}
    monkeypatch.setattr("src.ingestion.build_index", lambda **kwargs: captured.update(kwargs) or 1)

    ask_app.index_uploaded_pdf(
        b"bytes", "f.pdf", uploads_dir=tmp_path / "u", store_dir=tmp_path / "s"
    )

    assert captured["show_progress"] is False
