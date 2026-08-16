"""Tests for app/document_tools.py — whole-document summary/notes generation.

No real API calls: a fake OpenAI client stands in, so these test the
map-reduce logic, token accounting, and cost calculation deterministically.
"""

import pytest

import app.document_tools as tools


# --------------------------------------------------------------------------
# Fake OpenAI client — each call returns a fixed, small, countable response
# --------------------------------------------------------------------------
class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeUsage:
    def __init__(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeResponse:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, model, messages):
        self.calls.append({"model": model, "messages": messages})
        # Deterministic, cheap: 10 input tokens per 100 chars of user content,
        # fixed 5 output tokens — enough to make totals checkable exactly.
        user_content = messages[-1]["content"]
        prompt_tokens = max(1, len(user_content) // 10)
        return _FakeResponse(f"[summary of {len(user_content)} chars]", prompt_tokens, 5)


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeClient:
    def __init__(self) -> None:
        self.chat = _FakeChat()


@pytest.fixture
def fake_client(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(tools, "_client", lambda: client)
    return client


# ==========================================================================
# Chunk splitting
# ==========================================================================
def test_split_into_map_chunks_covers_the_whole_text_with_no_gaps():
    text = "x" * 2500
    chunks = tools._split_into_map_chunks(text, chunk_chars=1000)
    assert "".join(chunks) == text
    assert len(chunks) == 3  # 1000 + 1000 + 500


def test_split_into_map_chunks_handles_empty_text():
    assert tools._split_into_map_chunks("", chunk_chars=1000) == [""]


def test_split_into_map_chunks_single_chunk_when_text_fits():
    text = "short document"
    chunks = tools._split_into_map_chunks(text, chunk_chars=1000)
    assert chunks == [text]


# ==========================================================================
# Direct vs map-reduce path selection
# ==========================================================================
def test_short_document_uses_a_single_call(fake_client, monkeypatch):
    monkeypatch.setattr(tools, "DIRECT_CHAR_LIMIT", 1000)
    output = tools._generate("short text", tools.SUMMARY_SYSTEM_PROMPT, "summary")
    assert output.call_count == 1
    assert len(fake_client.chat.completions.calls) == 1


def test_long_document_uses_map_reduce_with_a_final_combine_call(fake_client, monkeypatch):
    monkeypatch.setattr(tools, "DIRECT_CHAR_LIMIT", 100)
    monkeypatch.setattr(tools, "MAP_CHUNK_CHARS", 40)
    text = "y" * 200  # 5 map chunks + 1 combine call

    output = tools._generate(text, tools.SUMMARY_SYSTEM_PROMPT, "summary")

    assert output.call_count == 6  # 5 partials + 1 combine
    assert len(fake_client.chat.completions.calls) == 6
    # The LAST call must be the combine call, using the caller's system
    # prompt, not the partial-summary prompt.
    last_call = fake_client.chat.completions.calls[-1]
    assert last_call["messages"][0]["content"] == tools.SUMMARY_SYSTEM_PROMPT


def test_map_reduce_partial_calls_use_the_partial_prompt_not_the_final_one(fake_client, monkeypatch):
    monkeypatch.setattr(tools, "DIRECT_CHAR_LIMIT", 10)
    monkeypatch.setattr(tools, "MAP_CHUNK_CHARS", 10)
    tools._generate("z" * 30, tools.NOTES_SYSTEM_PROMPT, "set of study notes")

    calls = fake_client.chat.completions.calls
    for call in calls[:-1]:  # every call except the final combine
        assert call["messages"][0]["content"] == tools.PARTIAL_SYSTEM_PROMPT


# ==========================================================================
# Token accounting — the total must be the SUM across every call, not just
# the final one, since the whole point is an honest cost figure.
# ==========================================================================
def test_map_reduce_sums_tokens_across_every_call(fake_client, monkeypatch):
    monkeypatch.setattr(tools, "DIRECT_CHAR_LIMIT", 10)
    monkeypatch.setattr(tools, "MAP_CHUNK_CHARS", 10)

    output = tools._generate("a" * 30, tools.SUMMARY_SYSTEM_PROMPT, "summary")

    manual_total_input = sum(
        max(1, len(call["messages"][-1]["content"]) // 10)
        for call in fake_client.chat.completions.calls
    )
    manual_total_output = 5 * len(fake_client.chat.completions.calls)
    assert output.input_tokens == manual_total_input
    assert output.output_tokens == manual_total_output


def test_direct_path_token_count_matches_the_single_call(fake_client, monkeypatch):
    monkeypatch.setattr(tools, "DIRECT_CHAR_LIMIT", 100_000)
    output = tools._generate("hello " * 20, tools.SUMMARY_SYSTEM_PROMPT, "summary")
    assert output.call_count == 1
    assert output.output_tokens == 5


# ==========================================================================
# Cost calculation
# ==========================================================================
def test_cost_usd_matches_verified_pricing():
    output = tools.DocumentOutput(text="x", input_tokens=1_000_000, output_tokens=1_000_000,
                                  latency_seconds=1.0, call_count=1)
    expected = tools.INPUT_COST_PER_MTOK + tools.OUTPUT_COST_PER_MTOK
    assert output.cost_usd() == pytest.approx(expected)


def test_cost_usd_zero_for_zero_tokens():
    output = tools.DocumentOutput(text="", input_tokens=0, output_tokens=0,
                                  latency_seconds=0.0, call_count=0)
    assert output.cost_usd() == 0.0


# ==========================================================================
# Public entry points wire to the right prompt
# ==========================================================================
def test_summarize_document_uses_the_summary_prompt(fake_client, monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "full_document_text", lambda _path: "doc text")
    tools.summarize_document(tmp_path / "f.pdf")
    call = fake_client.chat.completions.calls[-1]
    assert call["messages"][0]["content"] == tools.SUMMARY_SYSTEM_PROMPT


def test_generate_notes_uses_the_notes_prompt(fake_client, monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "full_document_text", lambda _path: "doc text")
    tools.generate_notes(tmp_path / "f.pdf")
    call = fake_client.chat.completions.calls[-1]
    assert call["messages"][0]["content"] == tools.NOTES_SYSTEM_PROMPT


def test_client_raises_a_clear_error_without_an_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        tools._client()
