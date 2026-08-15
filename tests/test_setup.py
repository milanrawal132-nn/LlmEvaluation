"""Phase 1 smoke test: is the environment actually wired up?

Run from the project root:  pytest -q

This does not test any logic — there isn't any yet. It checks the three things
that silently break a beginner's setup: wrong Python, missing packages,
missing API key.
"""

import os
import sys

import pytest


def test_python_version() -> None:
    """We use modern type-hint syntax (list[str], int | None) — needs 3.12+."""
    assert sys.version_info >= (3, 12), f"Need Python 3.12+, running {sys.version}"


def test_project_modules_import() -> None:
    """Our four src modules import cleanly (catches syntax errors early)."""
    from src import evaluation, generation, ingestion, retrieval  # noqa: F401


@pytest.mark.parametrize(
    "package",
    ["pypdf", "openai", "chromadb", "pandas", "tiktoken"],
)
def test_dependency_installed(package: str) -> None:
    """Every dependency in requirements.txt is importable."""
    __import__(package)


def test_api_key_present() -> None:
    """The OpenAI API key is set. Phase 4 fails without it."""
    from dotenv import load_dotenv

    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    assert key, "OPENAI_API_KEY not set — copy .env.example to .env and add your key"
    assert key != "sk-your-key-here", "OPENAI_API_KEY is still the placeholder value"


def test_retrieval_embeds_queries_with_ingestion_function() -> None:
    """Questions must be embedded by the SAME code that embedded the documents.

    Two different embedding models = two incompatible coordinate systems, and
    retrieval silently returns confident garbage with no error to catch.

    We assert identity of the *function*, not equality of a model-name string:
    sharing the function means the model, dimensions, and batching cannot drift
    apart even if someone edits one file and forgets the other.
    """
    from src import ingestion, retrieval

    assert retrieval.embed_texts is ingestion.embed_texts
