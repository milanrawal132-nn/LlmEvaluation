"""Semantic boundaries of the three LLM judges.

Two layers, because they catch different regressions:

  offline  the rubric TEXT still encodes each rule, and abstentions never
           reach the API. Fast, free, runs in the default suite.

  judge    the judge actually BEHAVES that way, on generic synthetic
           examples. Costs API calls, so it is marked and deselected by
           default:  pytest -m judge

Every example here is synthetic. None of them mentions a real question, a real
company, or a real figure from the corpus — a rubric that only works on the
25 pilot questions is a hack, not a calibration.
"""

import pytest

from src.evaluation import (
    judge_correctness,
    judge_faithfulness,
    judge_relevance,
)
from src.retrieval import RetrievedChunk


def _context(*texts: str) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(text=text, source_document="doc.pdf", chunk_index=i,
                       page_numbers=[1], score=0.7, start_char=0, end_char=len(text))
        for i, text in enumerate(texts)
    ]


# ==========================================================================
# Offline: abstentions must never cost an API call
# ==========================================================================
def _explode(*_args, **_kwargs):
    raise AssertionError("the judge called the API for an abstention")


def test_abstention_short_circuits_all_three_judges(monkeypatch):
    """Short-circuiting is behaviour, not an optimisation.

    It is what guarantees an abstention scores faithful/relevant regardless of
    what the model of the day thinks, and correct=False regardless too.
    """
    import src.evaluation as evaluation

    monkeypatch.setattr(evaluation, "_ask_judge_once", _explode)
    answer = "I don't know."

    assert judge_correctness(answer, "Nine.") is False
    assert judge_faithfulness(answer, _context("anything at all")) is True
    assert judge_relevance(answer, "How many meetings were held?") is True


# ==========================================================================
# Offline: the rubric text still says what it must
# ==========================================================================
def _prompt_for(judge, *args) -> str:
    """Capture the instruction a judge would send, without sending it."""
    captured: list[str] = []

    def spy(instruction: str, repetitions: int = 1) -> bool:
        captured.append(instruction)
        return True

    import src.evaluation as evaluation

    original = evaluation._ask_judge
    evaluation._ask_judge = spy
    try:
        judge(*args)
    finally:
        evaluation._ask_judge = original
    return captured[0]


def test_faithfulness_rubric_forbids_penalising_incompleteness():
    prompt = _prompt_for(judge_faithfulness, "Revenue was 100.", _context("Revenue was 100."))
    lowered = prompt.lower()
    assert "do not penalise missing information" in lowered
    assert "incompleteness" in lowered


def test_faithfulness_rubric_forbids_using_a_reference():
    prompt = _prompt_for(judge_faithfulness, "Revenue was 100.", _context("Revenue was 100."))
    assert "do not judge correctness" in prompt.lower()
    assert "reference" in prompt.lower()


def test_faithfulness_rubric_requires_more_than_the_value_appearing():
    """The rule that stops a date in a different role counting as support."""
    prompt = _prompt_for(judge_faithfulness, "x", _context("y"))
    assert "not sufficient on its own" in prompt.lower()


def test_relevance_rubric_forbids_requiring_completeness_or_correctness():
    prompt = _prompt_for(judge_relevance, "Revenue was 100.", "What was revenue?")
    lowered = prompt.lower()
    assert "partial answer" in lowered
    assert "do not judge whether the answer is correct" in lowered


def test_correctness_rubric_still_requires_every_reference_fact():
    """Correctness agreed with humans 25/25; this guards against drift."""
    prompt = _prompt_for(judge_correctness, "Revenue was 100.", "Revenue was 100.")
    assert "missing any one is no" in prompt.lower()


# ==========================================================================
# Behavioural: does the judge actually apply the rules?  pytest -m judge
# ==========================================================================
pytestmark_note = "these hit the OpenAI API; run with: pytest -m judge"


@pytest.mark.judge
def test_faithful_when_answer_is_incomplete_but_grounded():
    """Answering one of two things asked is not unfaithful — just incomplete."""
    context = _context("Total revenue was 100 crore. Net profit was 20 crore.")
    assert judge_faithfulness("Total revenue was 100 crore.", context) is True


@pytest.mark.judge
def test_faithful_when_answer_is_wrong_but_drawn_from_context():
    """Wrong-but-grounded. Correctness catches this; faithfulness must not.

    The context here supports the claim exactly as the answer makes it. That
    the gold reference says something else (because the right figure lives on
    a page retrieval never reached) is not faithfulness's business.
    """
    context = _context("Operating margin for the year was 25.3% on this basis.")
    assert judge_faithfulness("The operating margin was 25.3%.", context) is True


@pytest.mark.judge
def test_unfaithful_when_a_value_is_attached_to_the_wrong_entity():
    """The same trap as the wrong-semantic-role date, in numeric form.

    Both figures are present in the context, so a judge checking only whether
    the number appears would pass this. The claim being made about the number
    is what has to be supported.
    """
    context = _context(
        "Segment A revenue was 100 crore for the year. "
        "Segment B revenue was 250 crore for the year."
    )
    assert judge_faithfulness("Segment A revenue was 250 crore.", context) is False


@pytest.mark.judge
def test_unfaithful_when_a_value_appears_in_a_different_semantic_role():
    """A date present in the context, attached to a DIFFERENT claim."""
    context = _context(
        "The appointment of the director was approved by the shareholders at "
        "the annual general meeting held on 12 August 2025."
    )
    assert judge_faithfulness("The director was appointed on 12 August 2025.", context) is False


@pytest.mark.judge
def test_unfaithful_when_the_answer_adds_a_claim_the_context_lacks():
    context = _context("Total revenue was 100 crore for the year.")
    answer = "Total revenue was 100 crore, and the company opened three new plants."
    assert judge_faithfulness(answer, context) is False


@pytest.mark.judge
def test_unfaithful_when_the_answer_adds_a_qualifier_the_context_lacks():
    """A qualifier is part of the claim. 'excluding X' is a different fact."""
    context = _context(
        "Including the provisions notified during the year, the ratio "
        "increased by 4.0% year on year."
    )
    answer = "Excluding those provisions, the ratio increased by 4.0% year on year."
    assert judge_faithfulness(answer, context) is False


@pytest.mark.judge
def test_faithful_when_the_context_labels_the_value_the_same_way():
    """The lenient half of the same rule: matching label, messy surroundings."""
    context = _context(
        "Opening balance 500.00 400.00 Provision made during the year "
        "2,338.73 1,806.44 Amount paid during the year (2,338.73) (1,806.44)"
    )
    answer = "The amount paid during the year was 2,338.73."
    assert judge_faithfulness(answer, context) is True


@pytest.mark.judge
def test_faithful_despite_damaged_table_formatting():
    """Extracted tables lose column alignment; that is not the answer's fault."""
    context = _context(
        "Earnings per equity share \nEquity shares of par value ` 5/- each \n"
        "Basic (`) 2.23  71.58  64.50 \nDiluted (`)"
    )
    assert judge_faithfulness("Basic earnings per share was 71.58.", context) is True


@pytest.mark.judge
def test_relevant_when_the_answer_is_partial():
    question = "What was total revenue, and what was net profit?"
    assert judge_relevance("Total revenue was 100 crore.", question) is True


@pytest.mark.judge
def test_relevant_when_the_numbers_are_wrong():
    assert judge_relevance("Total revenue was 999 crore.", "What was total revenue?") is True


@pytest.mark.judge
def test_irrelevant_when_the_answer_is_about_another_subject():
    answer = "The board held nine meetings during the year."
    assert judge_relevance(answer, "What was total revenue?") is False


@pytest.mark.judge
def test_correct_accepts_equivalent_units():
    assert judge_correctness("Revenue was 28.40 crore.", "Revenue was 2,840.33 lakhs.") is True


@pytest.mark.judge
def test_incorrect_when_a_required_fact_is_missing():
    reference = "Revenue was 100 crore and net profit was 20 crore."
    assert judge_correctness("Revenue was 100 crore.", reference) is False


@pytest.mark.judge
def test_incorrect_when_a_value_is_wrong():
    assert judge_correctness("Revenue was 250 crore.", "Revenue was 100 crore.") is False
