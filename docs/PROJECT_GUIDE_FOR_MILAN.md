# LLMEvalIQ — The Complete Guide

**Everything this project does, why it does it, what else was on the table and why we didn't pick it, and how to talk about all of it in an interview.**

This is written to be read start to finish by someone who built parts of this project but wants the *whole* picture in one place — every term explained in plain language with a real example from this exact project, not a textbook example.

---

## Table of Contents

1. [The One-Paragraph Version](#1-the-one-paragraph-version)
2. [Core Concepts, Explained Simply](#2-core-concepts-explained-simply)
3. [Phase-by-Phase Walkthrough](#3-phase-by-phase-walkthrough)
4. [What We Used vs. What Else Existed — and Why](#4-what-we-used-vs-what-else-existed--and-why)
5. [Interview Question Bank](#5-interview-question-bank)
6. [Quick-Reference Glossary](#6-quick-reference-glossary)
7. [How to Tell This Story in an Interview](#7-how-to-tell-this-story-in-an-interview)

---

## 1. The One-Paragraph Version

We built a small system that answers questions about 12 real company annual reports by finding the relevant pages and asking an AI model to answer using only those pages (this is called **RAG** — Retrieval-Augmented Generation). Then we spent almost all our effort not on that system, but on **proving whether it actually works** — because a RAG system that sounds confident and a RAG system that's actually right look *identical* from the outside. We found that the system reached the right *document* 100% of the time but found the right *passage inside it* only ~20% of the time. We ran a controlled experiment to improve that, checked the improvement survived being re-run multiple times (because AI models give different answers to the same question), analyzed exactly where and why it still fails, measured what it costs, and packaged all of it into a report, a dashboard, and a live app.

---

## 2. Core Concepts, Explained Simply

Each term below: **what it means**, an **analogy**, and a **real example from this project**.

### RAG (Retrieval-Augmented Generation)
**What it means:** Instead of asking an AI model a question and letting it answer from memory, you first *retrieve* relevant text from your own documents, then hand that text to the AI and say "answer using only this."
**Analogy:** An open-book exam. The student (the AI) doesn't have to memorize the textbook — they just need to find the right page and read it correctly.
**Example here:** Ask "How many board meetings did Ecoplast hold?" → the system searches 22,832 (or 18,682, depending on config) chunks of text from 12 PDFs, pulls the 5 most relevant ones, and only THEN asks the AI to answer — using just those 5 snippets, nothing else.

### Embedding
**What it means:** A way of turning a piece of text into a list of numbers (a "vector") that captures its *meaning*. Two pieces of text with similar meaning get similar numbers, even if they don't share any words.
**Analogy:** GPS coordinates for meaning. Just like two houses close in physical distance have similar latitude/longitude, two sentences close in *meaning* have similar embedding vectors.
**Example here:** The question "What did Goa Carbon earn?" and the sentence "sales and other income was ₹70,879.78 lakhs" share almost no words, but their embeddings land close together — that's what makes the search work at all.

### Vector database
**What it means:** A database built to store these number-lists (vectors) and quickly find the ones most similar to a new vector.
**Analogy:** A library where books aren't organized by title, but by *topic similarity* — so asking for "a book about lions" finds nearby books about tigers and cheetahs too, even without those exact words in the request.
**Example here:** We used **Chroma**, storing one vector per chunk of text (22,832 of them at chunk_size=500).

### Cosine similarity (and cosine distance)
**What it means:** A number between -1 and 1 that measures how "aligned" two vectors are — 1 means identical meaning direction, 0 means unrelated, -1 means opposite. Chroma reports *distance* (1 − similarity), so a smaller distance means a better match.
**Analogy:** Imagine two arrows pointing out from the same origin. If they point almost the same direction, they're "similar," regardless of how long each arrow is.
**Example here:** In this project, the score for a genuinely correct match usually lands around 0.55–0.72. Anything a retrieved chunk scores near 0.71 for an EPS question is a strong match; a chunk scoring 0.50 for the same question is weak — we used this exact gap to diagnose the q021 failure (see Phase 7A/7B below).

### Chunk / chunk size / overlap
**What it means:** A document is too big to hand an AI model all at once (and most of it is irrelevant to any one question), so we cut it into smaller pieces ("chunks"). Chunk size is how many characters per piece; overlap is how many characters two consecutive chunks share, so a sentence sitting exactly on the cut point isn't sliced in half.
**Analogy:** Cutting a long roll of fabric into curtain-sized pieces, but leaving a little extra fabric at each seam so no pattern gets cut mid-motif.
**Example here:** At chunk_size=500/overlap=50, "Ecoplast's board met (X) times" might get physically split between two chunks if it sits near a 500-character boundary; at chunk_size=600 there's more room for a full sentence to survive intact in one chunk.

### Top-K retrieval
**What it means:** Of all the chunks in the vector database, take only the K closest matches to the question (we mostly used K=5) and hand *those* to the AI model.
**Analogy:** A librarian doesn't hand you the whole library when you ask a question — they hand you the 5 books that look most relevant, and you work from those.
**Example here:** TOP_K=5 across almost this whole project. Phase 5 also measured K=1/3/10 to see how the numbers changed as you look deeper.

### LLM (Large Language Model) / Generation model
**What it means:** The AI model that reads the retrieved chunks and the question, and writes an answer.
**Analogy:** The "student" in the open-book exam — reads what's put in front of it and answers, ideally without making anything up.
**Example here:** We used `gpt-4o-mini` for every generated answer in this project.

### System prompt
**What it means:** Fixed instructions given to the AI model before every question, shaping how it must behave — regardless of what the user asks.
**Analogy:** The exam rules printed at the top of the paper: "Use only the material provided. If you don't know, write 'I don't know' — do not guess."
**Example here:** Our system prompt explicitly forbids outside knowledge and mandates the exact phrase `"I don't know."` when the context doesn't contain the answer — this is *why* the live app often says "I don't know" instead of guessing.

### Token
**What it means:** The unit AI models actually process text in — roughly ¾ of a word in English, though it varies. Both cost and context-window limits are measured in tokens, not characters or words.
**Analogy:** Text is billed like a taxi meter — not by the kilometre (character), but by the "unit" the meter actually counts.
**Example here:** A typical answer in this project used ~850–1,000 input tokens and ~4–20 output tokens, costing about $0.00014–0.00016 per question at gpt-4o-mini's rates.

### Hallucination
**What it means:** The AI model stating something confidently that isn't actually true or supported by what it was given.
**Analogy:** A student inventing a plausible-sounding fact on an exam because they don't want to leave a blank answer.
**Example here:** For "What was Infosys's operating margin?", the model answered **25.3%** when the true figure was **20.3%** — stated with total confidence, from a real (but wrong) retrieved passage.

### Correctness vs. Faithfulness vs. Relevance
**What they mean, together:**
- **Correctness** — does the answer match the true/reference answer?
- **Faithfulness** — is every claim in the answer actually backed by the text the model was shown (regardless of whether that text was the RIGHT text)?
- **Relevance** — does the answer address the actual question asked?
**Analogy:** A weather forecaster who confidently reads out yesterday's forecast for today: relevant (it's still about the weather), faithful (they read it correctly off the report), but not correct (wrong day).
**Example here:** The Infosys margin example above is a perfect case: **faithful** (the number really was on a retrieved page) + **relevant** (it answers the question asked) + **not correct** (wrong number) — all three at once. This is exactly why you need all three metrics, not just one.

### Abstention
**What it means:** The system declining to answer ("I don't know") rather than guessing.
**Analogy:** A witness in court saying "I don't recall" instead of making up an answer under pressure — legally and practically the honest, correct move.
**Example here:** Across this project's 25 test questions, the system abstained on roughly **52–64%** of them. That sounds bad until you realize the alternative — guessing on all of those — would mean far more hallucinations, which is worse.

### Ground truth / Gold set
**What it means:** A hand-verified set of questions with known-correct answers and known-correct source locations, used to measure whether the system is actually working.
**Analogy:** An answer key for a test — without it, you can't grade anything, you can only guess whether an answer "sounds right."
**Example here:** 25 questions, each with 1+ pieces of required evidence, hand-checked against the actual PDF pages.

### Evidence / Evidence group / Evidence span
**What they mean:**
- **Evidence** — the specific fact a question needs, and where it lives in the source document.
- **Evidence group** — sometimes a fact appears in *more than one place* in the document (e.g. the same number in two different tables); a group bundles those together so finding *either* copy counts as success.
- **Evidence span** — the exact character position (start/end) of that fact in the extracted document text, so it can be checked against retrieval no matter how the document gets cut into chunks.
**Analogy:** A treasure hunt where the same treasure is buried in two different spots on the map — finding either spot wins, and the map marks the EXACT coordinates, not a vague "somewhere over there."
**Example here:** Question q019 asks for Infosys's EPS. That number (₹71.58) genuinely appears in **two different tables** in the report. Treating both as required would unfairly penalize the system for finding only one; treating them as a group (find either, credit either) is the honest scoring.

### LLM-as-judge
**What it means:** Using a second call to an AI model to *grade* whether an answer is correct/faithful/relevant, instead of grading by exact string match (which fails on things like "₹28.40 crore" vs "2,840.33 lakhs" — same fact, different words).
**Analogy:** A teaching assistant who reads a student's essay and judges whether it correctly answers the question, rather than a computer checking if the exact words match an answer key.
**Example here:** We asked a *second, separate* `gpt-4o-mini` call to judge each answer, three times per verdict (majority vote), then checked its judgments against a human's own review on the same 25 questions — landing at 100% correctness agreement, 92% faithfulness agreement, 100% relevance agreement.

### Failure taxonomy
**What it means:** A fixed set of categories every wrong (or right) answer gets sorted into, based on TWO questions: was the right evidence retrieved, and was the answer correct? This turns "it's wrong" into "it's wrong *in this specific way*," which tells you what to actually fix.
**Analogy:** A doctor doesn't just write "patient is sick" — they diagnose WHICH illness, because the treatment is completely different for each one.
**Example here:** Six categories used throughout this project — `grounded_correct`, `generation_failure`, `generation_refusal`, `unsupported_correct`, `retrieval_failure_honest`, `retrieval_failure_hallucinated`. See Phase 8 below.

### Controlled experiment / Pre-registered selection rule
**What it means:** Changing exactly ONE thing at a time while holding everything else fixed, and — crucially — **deciding in advance** what "success" will be measured by, before looking at the results. This stops you from unconsciously picking whichever result looks best after the fact.
**Analogy:** Deciding you'll pick the winning racehorse by *finishing time*, and writing that rule down BEFORE the race starts — not watching the race and then explaining afterward why the horse you liked "really" won.
**Example here:** We tested chunk sizes 300/500/600/1000, changing nothing else, and declared beforehand that the winner would be whichever scored highest on **Gold Span Coverage@5** — not Document Recall (which was maxed out at 100% for every size and couldn't discriminate anything).

### Statistical significance (and why we didn't claim it)
**What it means:** A formal mathematical test for whether a difference between two results is likely "real" or could easily be random chance, usually expressed as a p-value.
**Analogy:** Flipping a coin 3 times and getting heads twice doesn't prove the coin is biased — you'd need many more flips before you could say that with real confidence.
**Example here:** We ran each configuration 3 times and reported that the *observed ranges* didn't overlap (500: 8–12% correct; 600: 16–24% correct) — but with only 3 runs, that's a **descriptive** observation, not a statistically powered claim. We say this explicitly everywhere rather than implying more certainty than 3 data points can support.

### Latency and throughput
**What they mean:** Latency = how long one request takes. Throughput = how many requests you can handle per unit time.
**Analogy:** Latency is how long it takes one customer to be served at a counter; throughput is how many customers the counter can serve per hour.
**Example here:** Mean generation latency was ~1.0–1.1 seconds per question, and didn't meaningfully differ between chunk sizes.

### Map-reduce (for summarization)
**What it means:** When a document is too big to fit in one AI request, split it into pieces, summarize each piece separately ("map"), then combine those mini-summaries into one final summary ("reduce").
**Analogy:** Instead of one person reading an entire 500-page report and writing a summary, you split it among 10 people, each summarizes their 50 pages, and then one person combines those 10 summaries into a final one.
**Example here:** Built into the live app's Summary/Notes feature for uploaded documents — small documents (under ~60,000 characters) get summarized in one call; bigger ones get map-reduced automatically.

---

## 3. Phase-by-Phase Walkthrough

### Phase 0 — Concept
Defined the project as an **evaluation** project, not a chatbot project. The central idea, repeated throughout: *retrieval and generation fail independently*, so they must be measured independently. A 4-quadrant table (retrieval ✅/❌ × answer ✅/❌) framed every later phase.

### Phase 1 — Environment setup
Python 3.12+, curated `requirements.txt` (10 direct dependencies, each with a WHY comment), `.env`/`.env.example` split so secrets never get committed, and a smoke-test suite (`tests/test_setup.py`) checking Python version, imports, and API key presence.

### Phase 2 — Corpus
12 real annual reports (Alivus, Alu Wind, Ecoplast, Ganesh, Goa Carbon, Infosys, Mahindra, Reliance, Rishiroop, Sayaji, Sumit, Tata Motors), **3,129 pages total**, verified readable, verified no single document dominated the corpus.

### Phase 3 — Gold evaluation set
25 hand-written questions across easy/medium/difficult and 5 question types, each with verified evidence (the exact source text, page, and document). This went through real corrections: a candidate-finder tool to locate verifiable facts, a switch from "one evidence snippet per question" to a proper one-to-many schema after finding q010 needed 4 separate facts, and manual verification of every single row against the real PDF.

### Phase 4 — Basic RAG pipeline
Built `src/ingestion.py` (PDF → chunks → embeddings → vector store), `src/retrieval.py` (question → top-K chunks), `src/generation.py` (chunks + question → answer). Provenance (source document, page numbers, character offsets) is carried through every step — this is what makes every later metric possible.

### Phase 5 — Frozen retrieval baseline
The first real measurement, and the one that set the whole project's direction:

| K | Document Recall | Any Evidence Recall | Evidence Coverage |
|---|---|---|---|
| 5 | **100.0%** | 24.0% | **19.0%** |

**Document Recall = "did we reach the right 200-page report?"** — trivially easy, saturates almost immediately. **Evidence Coverage = "did we actually find the specific paragraph with the answer?"** — the honest number, and it's roughly 1-in-5. This gap is the single most important finding of the whole project.

### Phase 6 — Generation baseline
With retrieval this weak, correctness was low (8% single-run) and abstention was high (52%) — expected, not a bug, since the system prompt tells the model to say "I don't know" rather than guess. Found faithfulness ≠ correctness (the Infosys margin example above). Found the generator itself gives **different wording on identical re-runs** — this became the reason Phase 7B exists at all.

### Judge validation
Before trusting the LLM-as-judge's numbers, checked them against a human's own review of the same 25 answers: correctness 100% agreement, faithfulness 92%, relevance 100%. Explicitly labeled as a 25-question smoke test, not a statistically calibrated instrument — and the human labels are described as **AI-assisted manual review**, not independent blinded annotation, because that's what they actually are.

### Phase 7A — Chunk-size experiment
Tested chunk_size ∈ {300, 500, 600, 1000}, overlap fixed at 50, everything else identical. **Selected the winner by a rule written down BEFORE running generation** — Gold Span Coverage@5 — specifically to avoid picking whichever result looked best afterward.

| chunk_size | Gold Span Coverage@5 | chunks | index size | build time |
|---|---|---|---|---|
| 500 (baseline) | 19.7% | 22,832 | 259.1 MB | 552.9s |
| **600 (winner)** | **23.9%** | 18,682 | 222.9 MB | 491.7s |

Document Recall was deliberately **not** the deciding metric — it read 100% for every single chunk size, so it had zero power to distinguish a good choice from a bad one.

**A regression was found and reported, not hidden:** question q021 (Infosys client numbers) got *worse* at chunk_size=600. Direct investigation (embedding one specific chunk and comparing its similarity score) found the real cause: at 600, a neighbouring client-count TABLE scored higher similarity (0.65) than the chunk containing the actual answer (0.50, *below* the usual "real match" floor of 0.55) — the retriever picked the wrong-but-topically-similar content over the right one.

### Phase 7B — End-to-end robustness (3 independent runs)
Because generation is non-deterministic, ran the FULL pipeline (not just retrieval) 3 separate times per configuration:

| | 500 (baseline) | 600 (winner) |
|---|---|---|
| Correctness | mean 10.7%, range 8–12% | mean **20.0%**, range 16–24% |
| Faithfulness | mean 84.0% | mean 92.0% |

The ranges don't overlap — reported as a descriptive observation, explicitly not a formal significance claim (only 3 runs). Also surfaced `unsupported_correct` — 5 of 75 answers at 600 were *correct* with **no retrieved evidence supporting them**, most plausibly because `gpt-4o-mini` already knows some of these public facts from its own training, not because retrieval found them. Never counted as a pipeline win.

### Phase 8 — Failure analysis
Sliced the failure taxonomy by document, difficulty, and question type, to find WHERE failures cluster (not just how many). Found: **Goa Carbon abstained honestly 100% of the time** (its chunks embed unusually poorly against natural questions — a document-specific weakness, not a corpus-wide one), **Infosys hallucinated 3.6× more than average** (its tables read as topically confident even when wrong), **Ecoplast concentrated on the generation side** (evidence usually found, model still got it wrong). Explicitly flagged categories with too few questions (n≤4) as unreliable rather than treating them as findings.

### Phase 9 — Cost, latency, efficiency
Verified `gpt-4o-mini` pricing fresh against OpenAI's official page (dated, not assumed) before computing any dollar figure. Found three SEPARATE, sometimes-contradicting truths:
- **Retrieval infrastructure:** 600 is better on every axis (18.2% fewer chunks, 14.0% smaller index, 11.1% faster build).
- **Generation token cost:** 500 is cheaper per call (600 uses ~18% more input tokens per question, because bigger chunks = more text per prompt).
- **Outcome efficiency:** 600 is cheaper **per correct answer** ($0.00080 vs $0.00129) — it wastes fewer calls on wrong answers, so the extra per-call cost pays for itself.

### Phase 10 — Final report, dashboard, README, audit
Synthesized everything into `reports/FINAL_REPORT.md` (16 sections, one coherent story instead of pasted phase outputs), built `app/dashboard.py` (an **offline** dashboard — never calls an API, loads only from saved result files, so anyone can inspect the finished project with zero API key), rewrote `README.md` as a portfolio landing page, and audited the whole repository for secrets, stale claims, and broken references. One real finding fixed during the audit: `.gitignore` was silently excluding the ENTIRE `results/` folder — meaning every number this project produced would have been invisible to anyone cloning the repo. Fixed, without touching the actual result files.

### Bonus — Live Q&A app (`app/ask.py`)
Built *after* Phase 10, kept deliberately separate from the offline dashboard (that one must NEVER call an API; this one exists ONLY to call the API, on demand). Three modes: **Ask a question** (top-K retrieval, same code path as every evaluation phase), **Summary**, and **Notes** (both read the WHOLE document instead of top-K chunks, because summarizing needs everything, not a 5-chunk slice). Also supports uploading your own PDF, auto-embedding it into its own separate index (so it can never overwrite the curated 12-document corpus), then querying it the same three ways.

---

## 4. What We Used vs. What Else Existed — and Why

| Decision | What we used | Real alternatives that existed | Why we picked what we picked |
|---|---|---|---|
| **Embedding model** | `text-embedding-3-small` | `text-embedding-3-large` (better, pricier, bigger vectors), open-source models like `sentence-transformers` (free, no API, needs local compute), Cohere Embed | Small model was cheap enough to re-embed the whole corpus repeatedly across 4 chunk-size experiments without worrying about cost; the project's roadmap explicitly excluded "multiple embedding models" from v1 scope, so one well-chosen model beat testing several partially. |
| **Vector database** | Chroma (local, on-disk) | Pinecone / Weaviate / Qdrant (managed, cloud, better at huge scale), FAISS (pure library, no server, very fast but no metadata filtering built in) | Chroma needs zero external infrastructure — one folder on disk, `pip install`, done. At ~10,000–40,000 chunks, cloud-scale vector DBs solve a problem we didn't have; Chroma's built-in metadata storage (page numbers, offsets) was exactly what provenance tracking needed. |
| **Generation model** | `gpt-4o-mini` | `gpt-4o` (smarter, ~15× pricier), Claude, open-source Llama/Mistral (free to run, needs your own GPU) | Cheap enough to run the SAME 25 questions dozens of times (3 robustness runs × 4 chunk sizes × judge calls) for a few cents total. The roadmap explicitly said "do not test multiple LLMs" for v1 — one model, deeply understood, beats several models shallowly tested. |
| **Chunking strategy** | Fixed-size overlapping character chunks | Semantic chunking (cut at meaning boundaries using another model), sentence-based chunking, table-aware chunking (treat tables as separate structured units) | Fixed-size chunking is simple, fast, deterministic, and easy to reason about — exactly what a controlled experiment needs (you can change ONE number, chunk_size, and know that's the only thing that changed). Table-aware chunking would likely have fixed the q021 failure (Finding F), but it's flagged as genuine future work, not built now — added complexity the roadmap explicitly deferred. |
| **Judging method** | LLM-as-judge, checked against human labels | Exact string match (fails instantly — "₹28.40 crore" ≠ "2,840.33 lakhs" even though they're the same number), classic NLP metrics like BLEU/ROUGE (measure word overlap, not factual correctness), human-only grading (accurate but slow and expensive at scale) | String match and BLEU/ROUGE would have scored this project's correct answers as "wrong" purely for using different number formats. LLM-as-judge handles that correctly — but ONLY after being checked against real human judgment first, which is exactly what the judge-validation step did. |
| **Evidence matching** | Fixed character-offset spans + groups of alternatives | Simple text search per chunk (this is what we started with, and it broke — a snippet could straddle a chunk boundary and become unfindable at some chunk sizes but not others), exact single-location answer key (this is also what we started with, and it broke — some facts genuinely appear twice) | The ruler has to be fair across every chunk size being compared, or the "winner" of an experiment could just be whichever size happened to suit the ruler. Fixed offsets + groups fixed both real bugs found along the way. |
| **Chunk-size winner rule** | Gold Span Coverage@5, decided BEFORE seeing generation results | Document Recall (looked easiest, but was saturated at 100% everywhere — no signal), "eyeball it after seeing all the generation numbers" (tempting, but this is exactly how you fool yourself into picking whatever config already looks good) | Pre-registering the rule is what makes the eventual finding trustworthy — nobody can say the winner was cherry-picked after the fact, because the rule was written down first. |
| **Robustness check** | 3 independent full generation runs, ranges reported descriptively | 1 run (cheap, but can't tell a real effect from ordinary AI randomness), a formal significance test with p-values (would need far more than 3 runs to be valid, and the roadmap explicitly excluded "advanced statistical tests" from v1) | 3 runs is the minimum that can show a *range*, which is enough to say "this doesn't overlap with that" without pretending to a certainty the sample size can't support. |
| **Dashboard** | Streamlit | Flask + custom HTML/React (far more control, far more work), Gradio (built for ML demos, less suited to a multi-tab analysis dashboard), a static Jupyter notebook export | Streamlit turns a Python script into a working web page with almost no extra code — exactly right for a small team building a portfolio artifact quickly, and it has built-in testing support (`AppTest`) that let us verify the whole page renders correctly without a browser. |
| **What we deliberately did NOT build (v1 scope)** | — | Multiple LLMs, multiple embedding models, agent evaluation, prompt-injection testing, CI/CD pipelines, regression gates, a full human-evaluation platform, advanced statistics, Docker/Kubernetes | Every one of these is a real, valid thing a bigger project would eventually need. For v1, the goal was to deeply and correctly answer ONE question — "does this system actually work, and by how much did our change help?" — and each of these would have added scope without adding to that answer. |

---

## 5. Interview Question Bank

**Q: Walk me through this project in two minutes.**
A: "I built a RAG system over 12 real annual reports, then spent most of my effort proving whether it actually worked rather than assuming it did. The first real measurement found the system reached the right document 100% of the time but found the actual answer-bearing passage only ~20% of the time — those are very different things, and most naive evaluations only check the first one. I ran a controlled, pre-registered experiment across four chunk sizes and found one that improved evidence coverage by about 21% relative. Because AI generation is non-deterministic, I re-ran the full pipeline three times per configuration before trusting that improvement, and it held — correctness roughly doubled, from about 11% to 20%. Then I did failure analysis to find WHERE it still breaks, and a cost/latency analysis to understand what the improvement actually costs. Everything's packaged into a report, an offline dashboard, and a live app."

**Q: Why is "the system found the right document" not good enough as a metric?**
A: On a 200+ page report, almost any semantically-related question will retrieve a chunk from the right document — that's an easy bar. It says nothing about whether the SPECIFIC paragraph needed to answer the question was found. In this project, Document Recall was 100% while Evidence Coverage — did we find the actual passage — was only ~20%. Reporting only the first number would make a mostly-broken system look like it works.

**Q: How do you know your LLM judge is trustworthy?**
A: I checked its verdicts against a human's own review of the same answers, on the same 25 questions, BEFORE trusting any of its numbers. It agreed 100% on correctness, 92% on faithfulness, 100% on relevance. I'm explicit that this is a small-sample smoke test, not a statistically calibrated instrument, and that the "human" labels were AI-assisted manual review, not independent blind annotation — overstating either would be dishonest about what was actually measured.

**Q: What's the difference between correctness and faithfulness, and why do you need both?**
A: Correctness asks "does this match the true answer?" Faithfulness asks "is every claim actually backed by what the model was shown?" They can disagree in both directions. My clearest example: asked for Infosys's operating margin, the model confidently answered 25.3% when the truth was 20.3% — faithful (it really did read that number off a retrieved page) and relevant (on topic) but not correct (wrong page won the retrieval race). If I'd only measured correctness, I'd know it failed but not WHY — faithfulness told me it wasn't hallucinating from nowhere, it was reading a genuinely wrong source.

**Q: How did you pick the winning chunk size, and how do you know it wasn't cherry-picked?**
A: I wrote down the selection rule — Gold Span Coverage@5 — before running any generation. I deliberately did not use Document Recall, because it was saturated at 100% for every chunk size and had no power to discriminate a good choice from a bad one. Writing the rule down first is what makes the result defensible: nobody, including me, could nudge the outcome by picking whichever number looked best after seeing everything.

**Q: You said correctness "roughly doubled." Is that statistically significant?**
A: No, and I'm careful never to claim it is. I ran each configuration 3 times and observed non-overlapping ranges (8–12% vs 16–24%), which is a real, descriptive signal that the difference survived actual re-run noise — but 3 data points can't support a formal significance claim, and I say that explicitly rather than implying more certainty than the sample size earns.

**Q: What is `unsupported_correct` and why does it matter?**
A: It's an answer that matches the true answer but has NO retrieved evidence supporting it. The likely explanation is the model already knew the fact from its own training data — these are public annual reports, after all — not that my retrieval pipeline actually found it. I never count these as pipeline wins; they're a training-data contamination risk, and hiding them would make the system look better than the retrieval pipeline actually is.

**Q: Tell me about a specific failure you found and root-caused.**
A: Question q021 asked about Infosys's new client count. At the winning chunk size, the chunk containing the correct answer was intact and available — but a NEIGHBOURING chunk, a client-count table, scored a higher similarity to the question (0.65 vs 0.50) and got retrieved instead. I confirmed this by directly embedding both chunks and comparing scores. It's an embedding-ranking failure, not a retrieval-completeness failure — the right text existed and was indexed, it just lost a popularity contest to a wrong-but-topically-similar table.

**Q: How do you decide what NOT to build?**
A: I followed an explicit v1 scope: no multiple LLMs, no multiple embedding models, no agent evaluation, no CI/CD, no advanced statistics, no Docker. Each of those is legitimate work for a bigger version, but this project's actual question was "does this system work, and can I prove a specific change helped" — and none of those additions would have changed the answer to that question, they'd have just added surface area.

**Q: What would you do differently, or test next, with more time?**
A: A reranker specifically to fix the table-vs-prose ranking problem (Finding F). Hybrid retrieval (BM25 + embeddings) since the Goa Carbon weakness looks like a case where exact keyword matching would help where dense embeddings struggle. Table-aware chunking. A larger, stratified gold set so small-sample categories (some question types only had 1–2 questions) stop needing a warning label. And genuinely independent human annotation, since my current human-review layer is AI-assisted, not blind.

**Q: How much does this cost to run, and is a "better" configuration always more expensive?**
A: Not necessarily — and separating those questions was one of the more important findings. The winning chunk size uses about 18% MORE input tokens per call (bigger chunks = more text per prompt) — so it's more expensive PER CALL. But because it wastes far fewer calls on wrong answers, it's actually CHEAPER per CORRECT answer — $0.00080 vs $0.00129. "Cheaper per call" and "cheaper per successful outcome" are genuinely different claims, and conflating them would have given a wrong recommendation.

---

## 6. Quick-Reference Glossary

| Term | One-line meaning |
|---|---|
| RAG | Retrieve relevant text first, then generate an answer using only that text |
| Embedding | Text turned into numbers that capture meaning |
| Chunk | A piece of a document, small enough to search and hand to an AI model |
| Top-K | Only the K most relevant chunks are used, not the whole document |
| Cosine similarity | How aligned two embeddings are (closer to 1 = more similar meaning) |
| Hallucination | A confident but false or unsupported claim |
| Correctness | Does the answer match the truth? |
| Faithfulness | Is the answer backed by what was actually retrieved? |
| Relevance | Does the answer address the question asked? |
| Abstention | Saying "I don't know" instead of guessing |
| Gold set | Hand-verified questions + correct answers, used to measure the system |
| Evidence span | The exact character location of a fact in the source document |
| LLM-as-judge | Using a second AI call to grade an answer, checked against human judgment |
| Failure taxonomy | Fixed categories every answer gets sorted into, based on WHY it failed |
| Pre-registered rule | Deciding the success metric before seeing the results |
| Document Recall | Did we reach the right document? (easy, often saturated) |
| Evidence Coverage | Did we find the actual answer-bearing passage? (the honest number) |
| Map-reduce (summarization) | Summarize big documents in pieces, then combine the pieces |

---

## 7. How to Tell This Story in an Interview

A good structure, in order:

1. **The hook** — "Two RAG systems can look identical from the outside; I built the instruments to tell them apart."
2. **The headline finding** — 100% Document Recall, ~20% Evidence Coverage. This single number is the whole project's reason for existing.
3. **The experiment** — pre-registered chunk-size test, one metric decided in advance, honest reporting of a regression (q021) alongside the win.
4. **The robustness check** — why one run isn't enough, and what 3 runs actually proved (and didn't).
5. **The cost/efficiency nuance** — "better" isn't one number; retrieval infrastructure, generation cost, and outcome efficiency can point in different directions at once.
6. **The discipline** — what you refused to claim (statistical significance, independent human validation) is as important to mention as what you found. This is what separates a real evaluation from a marketing pitch.

If an interviewer only remembers one sentence: *"Document recall was already 100% while evidence coverage was only ~20% — and a controlled, pre-registered experiment closed part of that gap while nearly doubling end-to-end correctness, without me ever claiming more statistical certainty than three runs can actually support."*
