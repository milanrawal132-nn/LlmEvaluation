"""Build a BLIND human-labelling sheet for the 25 pilot questions.

Run from the project root, after a generation run has produced answers:
    ./.venv/bin/python -u scripts/make_human_review.py

Outputs two files:
    results/human_review_template.csv   <- fill this in
    results/human_review_context.md     <- read this while filling it in

The sheet deliberately does NOT contain the judge's verdicts.

That is the single most important property of this file. A human who can see
that the judge said YES will agree with it far more often than a human who
cannot — the label stops being an independent measurement and becomes a
review of the machine's homework. Agreement computed that way is inflated and
tells you nothing about whether the judge is any good.

Same reason the context lives in a separate document: the CSV stays narrow
enough to label quickly in a spreadsheet, and the full retrieved text (which
faithfulness genuinely requires) is read alongside it.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(".env"))

from src.retrieval import TOP_K, retrieve  # noqa: E402

QUESTIONS_CSV = Path("data/evaluation/questions.csv")
STORE_DIR = Path("data/chroma")
RESULTS_DIR = Path("results")

# Source of the answers to be labelled. The human must label the SAME answers
# the judge labelled, or the comparison is meaningless.
ANSWERS_CSV = RESULTS_DIR / "phase6_generation_majority3.csv"

TEMPLATE_CSV = RESULTS_DIR / "human_review_template.csv"
CONTEXT_MD = RESULTS_DIR / "human_review_context.md"

# Columns the human fills in. Left empty on purpose.
HUMAN_COLUMNS = ["human_correct", "human_faithful", "human_relevant", "notes"]


def main() -> None:
    if not ANSWERS_CSV.exists():
        raise SystemExit(
            f"{ANSWERS_CSV} not found. Run scripts/measure_generation.py first."
        )

    questions = {
        row["question_id"]: row
        for row in csv.DictReader(QUESTIONS_CSV.open(encoding="utf-8"))
    }
    answers = list(csv.DictReader(ANSWERS_CSV.open(encoding="utf-8")))

    rows = []
    context_blocks = []

    for answer_row in answers:
        qid = answer_row["question_id"]
        question = questions[qid]

        rows.append(
            {
                "question_id": qid,
                "question": question["question"],
                "reference_answer": question["reference_answer"],
                "model_answer": answer_row["answer"],
                # Blank for the human. Every other column above is context.
                **{column: "" for column in HUMAN_COLUMNS},
            }
        )

        # Faithfulness cannot be labelled without seeing what the model saw.
        chunks = retrieve(question["question"], STORE_DIR, k=TOP_K)
        block = [
            f"## {qid}",
            "",
            f"**Question:** {question['question']}",
            "",
            f"**Reference answer:** {question['reference_answer']}",
            "",
            f"**Model answer:** {answer_row['answer']}",
            "",
            f"**Retrieved context ({len(chunks)} chunks, the ONLY thing the model saw):**",
            "",
        ]
        for i, chunk in enumerate(chunks, start=1):
            pages = ", ".join(str(p) for p in chunk.page_numbers)
            block.append(
                f"<details><summary>[{i}] {chunk.source_document} "
                f"p.{pages} — score {chunk.score:.3f}</summary>\n\n"
                f"```\n{chunk.text}\n```\n\n</details>"
            )
        block.append("")
        context_blocks.append("\n".join(block))
        print(f"  {qid} prepared")

    RESULTS_DIR.mkdir(exist_ok=True)
    with TEMPLATE_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    CONTEXT_MD.write_text(
        "# Human review context — Phase 6 pilot\n\n"
        "Label in `results/human_review_template.csv`. Use `1` for yes, `0` for no.\n\n"
        "- **human_correct** — does the model answer state the same facts as the "
        "reference? Different units for the same amount still count as correct. "
        "If the reference states several facts, all of them are required.\n"
        "- **human_faithful** — is every claim in the model answer supported by "
        "the retrieved context below? Judge *support*, not truth: a claim that is "
        "true in the real world but absent from the context is NOT faithful.\n"
        "- **human_relevant** — does the answer address the question asked? "
        "Ignore whether it is correct. Right topic with wrong numbers is still "
        "relevant.\n"
        "- **notes** — anything ambiguous. These are the rows worth arguing about.\n\n"
        "An `I don't know.` answer counts as faithful and relevant (it asserts "
        "nothing and does address the question), and never correct.\n\n"
        "The judge's verdicts are deliberately not shown. Label independently, "
        "then run `scripts/compare_judge_to_human.py`.\n\n"
        + "\n---\n\n".join(context_blocks),
        encoding="utf-8",
    )

    print(f"\nwrote {TEMPLATE_CSV}  ({len(rows)} rows to label)")
    print(f"wrote {CONTEXT_MD}")
    print("\nJudge verdicts are NOT in either file — that is intentional.")


if __name__ == "__main__":
    main()
