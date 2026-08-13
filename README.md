# LLMEvalIQ v1

A small Retrieval-Augmented Generation (RAG) system — and, more importantly, the
instruments to measure whether it actually works.

**This is not a chatbot project. It is an evaluation project.**

Two RAG systems, one 60% correct and one 90% correct, look identical from the
outside. Both produce fluent, confident paragraphs. Fluency is not accuracy.
LLMEvalIQ measures the difference.

---

## What it measures

| Metric | Question it answers | What it catches |
|---|---|---|
| **Recall@K** | Did we retrieve the chunk containing the answer? | Broken retrieval — if the right page never arrives, no model can save you |
| **Correctness** | Does the answer match the reference answer? | The bottom-line score |
| **Faithfulness** | Is every claim supported by the retrieved chunks? | **Hallucination** |
| **Answer relevance** | Did it answer the question actually asked? | On-topic but wrong-question answers |
| **Latency** | Seconds per question? | Product viability |
| **Cost** | Tokens in/out → dollars? | Business viability at scale |

The central idea: **retrieval and generation fail independently.**

| Retrieval OK? | Answer OK? | Diagnosis | Where to fix |
|---|---|---|---|
| ✅ | ✅ | Working | — |
| ❌ | ❌ | **Retrieval failure** | chunking, K, embeddings |
| ✅ | ❌ | **Generation failure** | prompt, model |
| ❌ | ✅ | **Lucky / leaked** ⚠️ | answered from memory, not your docs — investigate |

That last row is why correctness alone is not enough to ship, and why Recall@K
and Faithfulness are separate metrics.

---

## Architecture

```
        ┌──────────── OFFLINE: run once, ahead of time ─────────────┐

         [ Documents ]              PDFs in data/documents/
               │
               ▼
         [ Split into chunks ]      500 chars, 50 overlap    ingestion.py
               │
               ▼
         [ Embeddings ]             text → vector            ingestion.py
               │
               ▼
         [ Vector store ]           ChromaDB on disk         ingestion.py
               │
        └──────┼────────────────────────────────────────────────────┘
               │
        ┌──────┼──────────── ONLINE: every user question ───────────┐
               │
   [ User question ] ──► [ Embed question ] ──► same vector space
               │                                       │
               │                                       ▼
               │                            [ Similarity search ]   retrieval.py
               │                                       │
               │                                       ▼
               │                            [ Top-K chunks ]  K=5
               │                                       │
               └───────────────┬───────────────────────┘
                               ▼
                    [ Prompt assembly ]                  generation.py
                    "Using ONLY the context
                     below, answer: <question>"
                               │
                               ▼
                        [   LLM   ]                      generation.py
                               │
                               ▼
                    [ Generated answer ]
                               │
                               ▼
              ╔════════════════════════════════════╗
              ║   EVALUATION LAYER                 ║     evaluation.py
              ║   judges, never modifies           ║
              ╚════════════════════════════════════╝
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        ▼          ▼           ▼           ▼          ▼
     Recall@K  Correctness Faithfulness Latency     Cost

        └───────────────────────────────────────────────────────────┘
```

Evaluation hangs off the *side* of the pipeline. It never changes the answer —
which is why `evaluation.py` is a separate file from `generation.py`.

---

## Installation

Requires **Python 3.12+** and an OpenAI API key.

```bash
git clone https://github.com/milanrawal132-nn/LlmEvaluation.git
cd LlmEvaluation

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # then edit .env and paste your real key
```

> **Secrets rule:** `.env` holds your real key and is gitignored.
> `.env.example` is a committed template and must never contain a real key.

Verify the setup:

```bash
pytest -q
```

---

## Folder structure

```
llmevaliq/
├── README.md
├── requirements.txt
├── .env.example              # template — no real secrets
├── .gitignore
│
├── data/
│   ├── documents/            # source PDFs (gitignored — large)
│   └── evaluation/
│       └── questions.csv     # gold ground truth (committed)
│
├── notebooks/
│   ├── 01_documents.ipynb    # corpus + building the gold set
│   ├── 02_basic_rag.ipynb    # one question, every step visible
│   └── 03_evaluation.ipynb   # scores, experiments, failure analysis
│
├── src/
│   ├── ingestion.py          # PDFs → chunks → embeddings → vector store
│   ├── retrieval.py          # question → top-K chunks
│   ├── generation.py         # chunks + question → answer
│   └── evaluation.py         # judges all of the above
│
├── tests/
└── results/                  # evaluation run outputs (gitignored)
```

One concept, one file. That is the whole architecture.

---

## Configuration

Every knob lives at the top of the file that owns it — there is no `config.py`,
deliberately.

| Parameter | Value | Defined in |
|---|---|---|
| `CHUNK_SIZE` | 500 | `src/ingestion.py` |
| `CHUNK_OVERLAP` | 50 | `src/ingestion.py` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | `src/ingestion.py` |
| `TOP_K` | 5 | `src/retrieval.py` |
| `MODEL` | `gpt-4o-mini` | `src/generation.py` |

`retrieval.py` **imports** `EMBEDDING_MODEL` rather than redeclaring it. Using
different embedding models for documents and questions is the #1 silent RAG
bug — the import makes it structurally impossible.

Pricing constants in `ingestion.py` and `generation.py` drive the Phase 9 cost
table. **Verify them against [OpenAI's pricing page](https://platform.openai.com/docs/pricing)**
before trusting any dollar figure — a stale constant makes every cost number wrong.

---

## How to run

Nothing to run yet — Phase 1 is project setup. Build order:

```bash
jupyter lab
```

1. `notebooks/01_documents.ipynb` — load the corpus, write `questions.csv`
2. `notebooks/02_basic_rag.ipynb` — one question end to end, every step printed
3. `notebooks/03_evaluation.ipynb` — score the full set, compare configs

---

## Example outputs

_Filled in from Phase 5 onward. Placeholder shape:_

```
Configuration: chunk=500 overlap=50 top_k=5 model=gpt-4o-mini

  Recall@1     0.__      Correctness   0.__
  Recall@3     0.__      Faithfulness  0.__
  Recall@5     0.__      Relevance     0.__
  Recall@10    0.__

  Mean latency   _._ s      Total cost  $_.__
```

---

## Roadmap

| Phase | Status |
|---|---|
| 0 — Concept | ✅ Done |
| 1 — Project setup | ✅ Done |
| 2 — Choose dataset | ⬜ Next |
| 3 — Gold evaluation set (60 easy / 30 medium / 10 hard) | ⬜ |
| 4 — Basic RAG, one configuration | ⬜ |
| 5 — Retrieval evaluation (Recall@K) | ⬜ |
| 6 — Answer evaluation (correctness, faithfulness, relevance) | ⬜ |
| 7 — Controlled experiment (chunk size 300 / 600 / 1000) | ⬜ |
| 8 — Failure analysis | ⬜ |
| 9 — Latency & cost | ⬜ |
| 10 — Streamlit dashboard | ⬜ |

**Deliberately out of scope for v1:** multiple LLMs, multiple embedding models,
agent evaluation, prompt-injection testing, CI/CD, regression gates, human
evaluation, advanced statistics, Docker. Those belong to later versions. v1
optimises for understanding.
