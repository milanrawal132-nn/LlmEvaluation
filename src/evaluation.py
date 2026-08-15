"""Judge the pipeline. This file never changes the answer — it only scores it.

That separation is the point of the whole project. Retrieval and generation
fail independently, so we measure them independently:

    Document Recall@K    did we reach the right report?        (Phase 5)
    Any Evidence@K       did we get at least one passage?      (Phase 5)
    Evidence Coverage@K  what FRACTION of required passages?   (Phase 5)
    Correctness          does the answer match the reference?  (Phase 6)
    Faithfulness         is every claim backed by the chunks?  (Phase 6)
    Relevance            did it answer the question asked?     (Phase 6)

Latency and cost are measured in generation.py (they come free with the API
call); Phase 9 just tabulates them.

The three retrieval metrics form a ladder from generous to honest. A question
needing four passages scores a full hit on the first two after retrieving one
of them; only coverage reports that three quarters of the evidence is missing.
"""

import re
from dataclasses import dataclass

from src.retrieval import RetrievedChunk

# Controlled vocabulary. Free-text values here would make Phase 8's
# failure-analysis breakdown meaningless.
QUESTION_TYPES = frozenset(
    {
        "numeric",      # an amount, count, percentage
        "entity",       # a name: person, subsidiary, plant, location
        "date",         # a date or period
        "list",         # a set of items: segments, risks, directors
        "comparison",   # requires weighing two values
        "descriptive",  # short prose. Hardest to grade — use sparingly.
    }
)

DIFFICULTIES = ("easy", "medium", "difficult")

# How a question's evidence rows combine. Stored per question in
# questions.csv, because it is a property of the QUESTION, not of any one
# passage.
#
#   "all"  conjunctive — every listed passage is required. The default, and
#          the right reading when each row carries a different fact
#          (q010 needs four segment revenues; three of four is not an answer).
#
#   "any"  disjunctive — the rows are alternatives, each independently
#          sufficient. q019's EPS appears in the ratios table AND again in the
#          consolidated statement; either one answers the question in full.
#
# Deliberately only two modes. Real gold sets eventually need evidence
# *groups* ("one of these two, plus that one"), but nothing in our 25
# questions needs that yet, and an unused abstraction is a liability.
EVIDENCE_MODES = ("all", "any")
DEFAULT_EVIDENCE_MODE = "all"

# A gold span counts as "hit" only when the retrieved chunks cover ALL of it.
# The one judgement call in the span metrics, so it is a named constant rather
# than a magic number buried in a comparison. Loosening it (say to 0.8) would
# make every configuration look better without retrieving anything more.
SPAN_HIT_THRESHOLD = 1.0


@dataclass
class Evidence:
    """One passage a question needs. A question may require several."""

    evidence_id: str
    question_id: str
    relevant_document: str
    relevant_pages: str
    evidence_text: str


@dataclass
class Scores:
    """Every metric for one question. One row of the Phase 6 results table."""

    question_id: str
    document_hit: bool        # generous: right report reached
    any_evidence_hit: bool    # middling: at least one passage reached
    evidence_coverage: float  # honest: fraction of required passages reached
    correctness: bool
    faithfulness: bool
    relevance: bool
    abstained: bool           # said "I don't know" instead of guessing
    failure_label: str        # which quadrant of the taxonomy this landed in


def normalise(text: str) -> str:
    """Collapse whitespace and lowercase, for tolerant text comparison.

    PDF extraction inserts line breaks, double spaces, and stray newlines at
    unpredictable places. A snippet copied from the PDF viewer will almost
    never be a byte-exact substring of the extracted text. Normalising both
    sides before comparing is what makes evidence matching usable in practice.

    Note this does NOT normalise punctuation: our corpus contains both U+0027
    and U+2019 apostrophes, in different documents. Snippets must be copied
    from the extracted text, and the Phase 3.3 check enforces that.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def normalised_with_offsets(text: str) -> tuple[str, list[int]]:
    """normalise(text), plus the raw index each normalised character came from.

    This is what makes gold offsets DERIVABLE instead of hand-entered. Evidence
    snippets were verified against normalised text (PDF extraction scatters
    line breaks, so byte-exact matching is hopeless), but offsets have to be
    expressed in RAW coordinates — the ones chunks are cut on. This function
    is the bridge between the two.

    offsets[i] is the raw index of normalised character i. A run of whitespace
    collapses to one space carrying the index of the run's FIRST character.

    Returns a string guaranteed equal to normalise(text); the caller asserts it.
    """
    chars: list[str] = []
    offsets: list[int] = []
    in_whitespace = False

    for index, char in enumerate(text):
        if char.isspace():
            if not in_whitespace:
                chars.append(" ")
                offsets.append(index)
                in_whitespace = True
            continue
        in_whitespace = False
        # A few characters lowercase to more than one (e.g. U+0130). Repeat the
        # source index so the two lists stay the same length — otherwise every
        # offset after such a character would be silently shifted.
        lowered = char.lower()
        chars.extend(lowered)
        offsets.extend([index] * len(lowered))

    start, end = 0, len(chars)
    while start < end and chars[start] == " ":
        start += 1
    while end > start and chars[end - 1] == " ":
        end -= 1
    return "".join(chars[start:end]), offsets[start:end]


@dataclass
class GoldSpan:
    """One evidence passage as a fixed character range in its source document.

    DERIVED, never hand-written. Typing offsets into a CSV by hand would be
    unverifiable and would rot the moment a PDF was re-extracted; these come
    from locating the already-verified evidence_text in the source text.

    Unlike text-substring matching, this range does not move when chunk_size
    changes — which is the only reason a cross-configuration comparison is
    possible at all.
    """

    evidence_id: str
    question_id: str
    source_document: str
    start_char: int
    end_char: int
    # Which required FACT this span is a location of. Spans sharing a group_id
    # are alternative locations of the same fact, each independently
    # sufficient; different groups are different facts, all required.
    #
    # Empty means "its own group", so an ungrouped span behaves exactly as it
    # did before groups existed.
    group_id: str = ""

    def group(self) -> str:
        return self.group_id or self.evidence_id


def _require_offsets(retrieved: list[RetrievedChunk], k: int) -> None:
    """Fail loudly on an index built before offsets existed.

    Without this the span metrics would score a stale index as 0% and look
    like a catastrophic retrieval regression.
    """
    for chunk in retrieved[:k]:
        if chunk.start_char is None or chunk.end_char is None:
            raise ValueError(
                "retrieved chunks carry no start_char/end_char — this index "
                "predates Phase 7A. Rebuild it with scripts/build_index.py."
            )


def _covered_fraction(span: GoldSpan, retrieved: list[RetrievedChunk], k: int) -> float:
    """Fraction of one gold span covered by the UNION of the top-k chunks.

    The union is the point. Text matching demanded that a single chunk contain
    the whole snippet, so a passage split across two adjacent chunks scored
    zero even though the model was shown every word of it. Here two adjacent
    chunks that jointly cover the span score 1.0 — which is what actually
    happened from the model's perspective.

    Only chunks from the SAME document contribute. Offsets are per-document
    coordinates; mixing them would let a chunk from Infosys "cover" a span in
    Goa Carbon because the numbers happened to overlap.
    """
    length = span.end_char - span.start_char
    if length <= 0:
        return 0.0

    intervals = sorted(
        (chunk.start_char, chunk.end_char)
        for chunk in retrieved[:k]
        if chunk.source_document == span.source_document
    )

    # Sweep left to right, merging overlaps via a cursor. Sorting by start is
    # what makes this correct: the cursor can never need to move backwards.
    covered = 0
    cursor = span.start_char
    for chunk_start, chunk_end in intervals:
        begin = max(chunk_start, cursor)
        finish = min(chunk_end, span.end_char)
        if finish > begin:
            covered += finish - begin
            cursor = finish
        if cursor >= span.end_char:
            break
    return covered / length


def group_coverages(
    retrieved: list[RetrievedChunk],
    spans: list[GoldSpan],
    k: int,
) -> dict[str, float]:
    """How well each required FACT was covered: group_id -> best alternative.

    MAXIMUM across a group's alternatives, not mean. The alternatives are the
    same fact written in two places, so finding either one satisfies the
    requirement completely. Averaging them would penalise retrieval for not
    finding a duplicate of something it already has — the same mistake the
    old row-level metric made on q019.

    This is what the duplicate-passage discovery forced. q010's four facts
    each appear verbatim on Ecoplast p.43 and p.70. A single fixed span would
    mark the p.43 copy as a miss purely because a human happened to verify
    p.70, which measures the annotator, not the retriever.
    """
    _require_offsets(retrieved, k)
    best: dict[str, float] = {}
    for span in spans:
        fraction = _covered_fraction(span, retrieved, k)
        key = span.group()
        best[key] = max(best.get(key, 0.0), fraction)
    return best


def gold_span_any_recall_at_k(
    retrieved: list[RetrievedChunk],
    spans: list[GoldSpan],
    k: int,
) -> bool:
    """Was at least one required fact FULLY covered by the top-k chunks?

    Full coverage, not "any overlap". One character of accidental overlap is
    not evidence the model could answer from; a completely covered span is.
    """
    return any(
        value >= SPAN_HIT_THRESHOLD
        for value in group_coverages(retrieved, spans, k).values()
    )


def gold_span_coverage_at_k(
    retrieved: list[RetrievedChunk],
    spans: list[GoldSpan],
    k: int,
    mode: str = DEFAULT_EVIDENCE_MODE,
) -> float:
    """How much of the question's gold evidence did the top-k chunks cover?

    Two levels, and keeping them straight is the whole design:

        WITHIN a group   max over alternative locations of one fact
        ACROSS groups    combined by evidence_mode

    Graded, not binary: a span half-covered scores 0.5, so a configuration
    that nearly reaches a passage is distinguishable from one that misses it
    entirely. That resolution is what makes chunk sizes comparable.

    evidence_mode across groups, same semantics as the text-based metric:
      "all" -> mean across required groups. Each fact weighted equally, so one
               long passage cannot dominate three short ones.
      "any" -> best single group.
    """
    if mode not in EVIDENCE_MODES:
        raise ValueError(f"evidence_mode must be one of {EVIDENCE_MODES}, got {mode!r}")
    if not spans:
        return 0.0

    fractions = list(group_coverages(retrieved, spans, k).values())
    if mode == "any":
        return max(fractions)
    return sum(fractions) / len(fractions)


def first_gold_span_rank(
    retrieved: list[RetrievedChunk],
    spans: list[GoldSpan],
) -> int | None:
    """1-based rank of the first chunk touching any gold span; None if none do.

    Reported as a distribution in Phase 7A. Rank answers a question the
    recall metrics cannot: when a configuration misses, did it miss narrowly
    (rank 7) or completely (rank 400)? Those need different fixes.

    Overlap here is ANY overlap, deliberately — this measures where the
    retriever started getting warm, not whether it succeeded.
    """
    _require_offsets(retrieved, len(retrieved))
    for rank, chunk in enumerate(retrieved, start=1):
        for span in spans:
            if (
                chunk.source_document == span.source_document
                and chunk.start_char < span.end_char
                and span.start_char < chunk.end_char
            ):
                return rank
    return None


def _matched_evidence_ids(
    retrieved: list[RetrievedChunk],
    evidence: list[Evidence],
    k: int,
) -> set[str]:
    """Which required passages appear inside the top-k retrieved chunks?

    Matching is per-chunk and strict: the snippet must sit wholly inside one
    chunk. We deliberately do NOT concatenate the top-k and search the joined
    text — the chunks are not adjacent in the source, so a match spanning two
    of them would be an artefact of retrieval order, not evidence the model
    ever saw the passage intact.

    The cost of that strictness is real: a snippet longer than CHUNK_OVERLAP
    that straddles a chunk boundary sits in no single chunk and can never
    match. `unfindable_evidence()` measures how much of the gold set that
    affects, so the artefact is reported rather than silently depressing scores.
    """
    windows = [normalise(chunk.text) for chunk in retrieved[:k]]
    return {
        item.evidence_id
        for item in evidence
        if any(normalise(item.evidence_text) in window for window in windows)
    }


def document_recall_at_k(
    retrieved: list[RetrievedChunk],
    evidence: list[Evidence],
    k: int,
) -> bool:
    """Did ANY of the top k chunks come from a document this question needs?

    The most generous metric, and weak on large documents: our 590-page report
    contributes ~4,100 chunks that all satisfy it. Reported mainly as a
    contrast — the gap between this and coverage is itself the finding.
    """
    wanted = {item.relevant_document for item in evidence}
    return any(chunk.source_document in wanted for chunk in retrieved[:k])


def any_evidence_at_k(
    retrieved: list[RetrievedChunk],
    evidence: list[Evidence],
    k: int,
) -> bool:
    """Did the top k chunks contain at least one required passage?

    Equivalent to evidence_coverage_at_k(...) > 0. Kept separate because it is
    the number comparable to the single-evidence metric used before the schema
    became one-to-many.
    """
    return bool(_matched_evidence_ids(retrieved, evidence, k))


def evidence_coverage_at_k(
    retrieved: list[RetrievedChunk],
    evidence: list[Evidence],
    k: int,
    mode: str = DEFAULT_EVIDENCE_MODE,
) -> float:
    """How much of this question's evidence requirement did retrieval satisfy?

    The honest retrieval metric — and the only one whose meaning depends on
    how the question's evidence combines:

      mode="all"  fraction of required passages retrieved. Four needed, one
                  found -> 0.25. Partial credit is meaningful here, because
                  each missing passage is a missing fact.

      mode="any"  1.0 if ANY listed passage was retrieved, else 0.0. No
                  partial credit, because there is nothing partial about it:
                  one sufficient passage is the whole requirement met, and
                  scoring 0.5 would penalise retrieval for not finding a
                  second copy of a fact it already found.

    Interacts with CHUNK_SIZE by design: passages sitting close together in the
    source can share a chunk, so larger chunks raise coverage while lowering
    precision. Phase 7's chunk-size sweep should show exactly that trade.
    """
    if mode not in EVIDENCE_MODES:
        raise ValueError(f"evidence_mode must be one of {EVIDENCE_MODES}, got {mode!r}")
    if not evidence:
        return 0.0

    matched = _matched_evidence_ids(retrieved, evidence, k)
    if mode == "any":
        return 1.0 if matched else 0.0
    return len(matched) / len(evidence)


def unfindable_evidence(
    evidence: list[Evidence],
    all_chunk_texts: list[str],
) -> list[str]:
    """Evidence IDs that sit inside NO single chunk in the index.

    A ruler-quality check, not a retrieval metric. If a snippet straddles a
    chunk boundary it can never be matched, so its question's coverage is
    capped below 1.0 no matter how good retrieval is. Run this before trusting
    any coverage number — otherwise a chunking artefact reads as a retrieval
    failure.
    """
    windows = [normalise(text) for text in all_chunk_texts]
    return [
        item.evidence_id
        for item in evidence
        if not any(normalise(item.evidence_text) in window for window in windows)
    ]


# --------------------------------------------------------------------------
# Abstention
# --------------------------------------------------------------------------
# generation.py's system prompt mandates this exact string. Detecting it needs
# no LLM call, so we do it with a substring test — cheaper, instant, and
# perfectly reliable *because we control the prompt that produces it*.
#
# Kept as a constant rather than a literal so the prompt and the detector
# cannot drift apart. If you edit SYSTEM_PROMPT, this must change with it.
ABSTENTION_PHRASE = "i don't know"


def is_abstention(answer: str) -> bool:
    """Did the model decline to answer rather than guess?

    Abstention is not a failure — it is the *correct* behaviour when retrieval
    brought back nothing useful. A system that abstains on a bad retrieval is
    strictly better than one that invents a number, even though both score
    zero on correctness. Phase 6 reports it separately so that difference is
    visible instead of being averaged away.

    We check `startswith` on the normalised text, not `in`, so an answer that
    merely mentions the phrase ("the report does not say, so I don't know
    whether...") while still asserting facts is not misread as an abstention.
    """
    return normalise(answer).startswith(ABSTENTION_PHRASE)


# --------------------------------------------------------------------------
# LLM-as-judge
# --------------------------------------------------------------------------
# Judging is a separate LLM call from answering, on purpose. Asking a model to
# grade its own answer in the same call lets it rationalise: it has already
# committed to the answer and will defend it. A fresh call sees only the text.
JUDGE_MODEL = "gpt-4o-mini"

# Temperature 0 asks for the most likely token every time. It does NOT
# guarantee determinism: measured over 75 verdicts in Phase 6, two moved
# between runs. So low temperature is necessary but not sufficient.
JUDGE_TEMPERATURE = 0.0

# ...which is why every judged metric is a majority vote of independent calls.
# An odd number so there is never a tie. Three is the cheapest odd number that
# can outvote a single stray verdict, and Phase 6 showed strays arriving about
# 1 verdict in 40.
#
# This is a property of the RULER, not of the pipeline under test. Retrieval
# and generation settings stay frozen at the Phase 5 baseline.
JUDGE_REPETITIONS = 3


def _ask_judge_once(instruction: str) -> bool:
    """One yes/no verdict from the judge model.

    Returns True only on an explicit YES. Anything unparseable counts as NO,
    which biases every metric DOWNWARD. That direction is deliberate: a
    silently-inflated score is far more dangerous than a pessimistic one.
    """
    import os

    from openai import OpenAI

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set — copy .env.example to .env")

    response = OpenAI(api_key=key).chat.completions.create(
        model=JUDGE_MODEL,
        temperature=JUDGE_TEMPERATURE,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict evaluation judge. Reply with exactly one "
                    "word: YES or NO. No explanation, no punctuation."
                ),
            },
            {"role": "user", "content": instruction},
        ],
    )
    verdict = (response.choices[0].message.content or "").strip().upper()
    return verdict.startswith("YES")


def _ask_judge(instruction: str, repetitions: int = JUDGE_REPETITIONS) -> bool:
    """Majority verdict over `repetitions` independent judge calls.

    Pass repetitions=1 to reproduce the single-run diagnostics.

    Note the calls are independent — we do NOT show the judge its own previous
    answers. Doing so would collapse the vote: the model would simply agree
    with itself, and three calls would cost 3x for the reliability of one.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")

    votes = [_ask_judge_once(instruction) for _ in range(repetitions)]
    return sum(votes) * 2 > repetitions


def judge_correctness(
    answer: str,
    reference_answer: str,
    repetitions: int = JUDGE_REPETITIONS,
) -> bool:
    """Does the answer agree with the human-written reference answer?

    String comparison fails here — "₹2,840.33 lakhs" and "₹28.40 crore" are the
    same fact, and our corpus states figures both ways. So we use an LLM as the
    judge, with the reference answer in hand.

    Semantics, stated explicitly:
      - the answer must state ALL facts the reference requires
      - a missing required fact makes correctness false
      - a wrong factual value makes correctness false
      - extra correct detail is acceptable

    The rubric is asymmetric on purpose. We ask whether the answer contains the
    reference's facts, NOT whether the two texts match: extra correct context
    is fine, a missing required fact is not. A question asking for two numbers
    is not answered correctly by one of them.

    NOT CHANGED during the judge calibration: this rubric already agreed with
    human labels on 25 of 25, so it was left byte-identical rather than
    "improved" into a regression.
    """
    if is_abstention(answer):
        # Short-circuit: "I don't know" never matches a reference answer, and
        # spending an API call to confirm that would be theatre.
        return False

    return _ask_judge(
        "Does the ANSWER state the same facts as the REFERENCE?\n\n"
        "Rules:\n"
        "- Numbers must agree in value. Different units or formats expressing "
        "the same amount agree (e.g. 2,840.33 lakhs = 28.40 crore).\n"
        "- If the REFERENCE states several facts, the ANSWER must state all of "
        "them. Missing any one is NO.\n"
        "- Extra correct detail in the ANSWER is acceptable.\n"
        "- Contradicting the REFERENCE on any point is NO.\n\n"
        f"REFERENCE: {reference_answer}\n\nANSWER: {answer}",
        repetitions,
    )


def judge_faithfulness(
    answer: str,
    chunks: list[RetrievedChunk],
    repetitions: int = JUDGE_REPETITIONS,
) -> bool:
    """Is every claim in the answer supported by the retrieved chunks?

    This is the hallucination detector. Note it does NOT look at the reference
    answer: an answer can be factually right and still unfaithful, if the model
    pulled it from training data rather than from our documents. Our corpus is
    public — Infosys and Reliance annual reports are certainly in the model's
    training data — so this metric is what separates "the RAG system worked"
    from "the model already knew".

    Semantics, stated explicitly:
      - judge ONLY the claims the answer actually makes
      - incompleteness is NOT unfaithfulness; a partial answer can be faithful
      - never compare against the reference answer here
      - wrong-but-grounded is faithful; the answer can be worthless and still
        be an accurate reading of what it was shown
      - a value merely appearing in context is not support. The surrounding
        text must back the claim being made ABOUT that value: "approved at the
        meeting on 12 August" does not support "took effect on 12 August"
      - an abstention asserts nothing and is faithful

    Calibrated against human labels. Before calibration this judge was wrong
    in BOTH directions at once — too generous where a date appeared in a
    different semantic role, too strict where the answer was incomplete or
    the extracted table was messy.
    """
    if is_abstention(answer):
        # An abstention asserts nothing, so nothing in it can be unsupported.
        # Scoring it False would punish exactly the behaviour we want.
        return True

    context = "\n\n".join(
        f"[{i}] {chunk.text}" for i, chunk in enumerate(chunks, start=1)
    )
    return _ask_judge(
        "Is every factual claim the ANSWER actually makes supported by the "
        "CONTEXT?\n\n"
        "Judge ONLY what the ANSWER asserts:\n"
        "- Do NOT penalise missing information, incompleteness, or a partial "
        "answer. Facts the ANSWER never mentions are irrelevant here.\n"
        "- Do NOT judge correctness, and do not compare against any reference. "
        "An ANSWER may be factually wrong and still be supported, if the "
        "CONTEXT is what it drew the claim from.\n"
        "- An ANSWER that declines to answer asserts nothing and is supported.\n"
        "\n"
        "Method — apply this to EVERY claim the ANSWER makes:\n"
        "  1. Take the value the ANSWER states, and the label the ANSWER "
        "attaches to it (what it says the value IS).\n"
        "  2. Find that value in the CONTEXT and read the label the CONTEXT "
        "attaches to it.\n"
        "  3. If those two labels describe different things, the claim is NOT "
        "supported, even though the value appears.\n\n"
        "Applying that method:\n"
        "- A value appearing somewhere in the CONTEXT is NOT sufficient on its "
        "own. CONTEXT saying a decision was APPROVED at a meeting on a date "
        "does not support an ANSWER saying the decision was MADE on that "
        "date — different labels, same value.\n"
        "- Qualifiers are part of the label and must match. 'excluding X' is "
        "not 'including X'; 'standalone' is not 'consolidated'; a figure for "
        "one entity, segment, or period does not support a claim about "
        "another.\n"
        "- Conversely, if the CONTEXT labels the value with the SAME thing the "
        "ANSWER claims, the claim is supported — even when the layout is "
        "broken, other numbers sit alongside it, or the period must be read "
        "from the column order. Extracted tables lose their alignment, and "
        "that is not the ANSWER's fault.\n"
        "- In a table row, the row's label applies to EVERY value on that row; "
        "the several values are that same metric across periods. An ANSWER "
        "naming that metric and quoting one of those values IS supported. "
        "Treat it as unsupported only if the ANSWER also asserts a period the "
        "CONTEXT plainly contradicts.\n"
        "- Reasonable paraphrase of the CONTEXT is supported. Wording that "
        "adds a qualifier or a meaning the CONTEXT does not carry is not.\n\n"
        "Answer NO only if some claim the ANSWER actually makes is "
        "unsupported.\n\n"
        f"CONTEXT:\n{context}\n\nANSWER: {answer}",
        repetitions,
    )


def judge_relevance(
    answer: str,
    question: str,
    repetitions: int = JUDGE_REPETITIONS,
) -> bool:
    """Does the answer address the question that was actually asked?

    Catches the on-topic-but-wrong-question failure: asked for FY2025-26
    revenue, answered with FY2024-25 profit. Both are about the same company
    and the same financial statement, so correctness alone reports a bare
    "wrong" without telling you the model misread the question.

    Semantics, stated explicitly:
      - judge subject matter ONLY
      - do not require completeness: a partial answer is relevant
      - do not require correctness: wrong values are relevant
      - an abstention is relevant
      - only off-topic answers are irrelevant

    Calibrated against human labels. Before calibration this judge was
    penalising incompleteness, which is what correctness measures.
    """
    if is_abstention(answer):
        # Declining IS a response to the question asked, and it is not an
        # answer to some other question. Excluded from the metric's meaning
        # rather than scored — the scripts report abstention separately.
        return True

    return _ask_judge(
        "Does the ANSWER address the subject the QUESTION asks about?\n\n"
        "Judge topic ONLY:\n"
        "- Do NOT judge whether the ANSWER is correct, complete, or supported "
        "by any source. Those are separate metrics.\n"
        "- A partial answer that addresses the QUESTION is relevant. Answering "
        "one of two things asked is still on topic.\n"
        "- An ANSWER with wrong values is relevant if it is answering the "
        "requested topic.\n"
        "- An ANSWER that declines to answer is relevant.\n\n"
        "Answer NO only when the ANSWER is about a different subject than the "
        "QUESTION — a different entity, period, or metric than the one asked "
        "about.\n\n"
        f"QUESTION: {question}\n\nANSWER: {answer}",
        repetitions,
    )


# --------------------------------------------------------------------------
# Failure taxonomy
# --------------------------------------------------------------------------
# The six outcomes a question can land in. The point of this table is that
# "wrong answer" is not one bug — it is at least three, with different fixes,
# and averaging them into a single accuracy number hides which one you have.
FAILURE_LABELS = {
    "grounded_correct": "Evidence retrieved, answer correct. The system worked.",
    "generation_failure": "Evidence WAS retrieved and the answer is still wrong. Fix the prompt/model.",
    "generation_refusal": "Evidence WAS retrieved and the model abstained anyway. Fix the prompt.",
    "unsupported_correct": "Correct WITHOUT the evidence. Memorised or lucky — do not count as a win.",
    "retrieval_failure_honest": "No evidence, and the model said so. Correct behaviour on a bad retrieval.",
    "retrieval_failure_hallucinated": "No evidence, and the model answered anyway. The worst quadrant.",
}


def classify_failure(evidence_retrieved: bool, correct: bool, abstained: bool) -> str:
    """Place one question in the failure taxonomy.

    The split is on `evidence_retrieved` FIRST, because that is what decides
    which half of the pipeline to go and fix. Only inside each half does the
    answer quality matter.

    Args:
        evidence_retrieved: Did the top-K chunks contain at least one required
            passage? (any_evidence_at_k — the generous reading, so that a
            question is only called a retrieval failure when it truly got
            nothing.)
        correct: judge_correctness verdict.
        abstained: is_abstention verdict.
    """
    if evidence_retrieved:
        if correct:
            return "grounded_correct"
        return "generation_refusal" if abstained else "generation_failure"

    if correct:
        # Right answer, no supporting evidence in context. Either the model
        # recalled it from training data, or the gold snippet is too narrow.
        # Both need a human to look — never bank this as a success.
        return "unsupported_correct"
    return "retrieval_failure_honest" if abstained else "retrieval_failure_hallucinated"
