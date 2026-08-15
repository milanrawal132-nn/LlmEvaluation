# Phase 5 retrieval baseline — FROZEN 2026-08-13

Do not regenerate. Phase 7 compares against these numbers.

Configuration measured (all untouched since Phase 4):
  CHUNK_SIZE=500  CHUNK_OVERLAP=50  TOP_K=5
  embeddings: text-embedding-3-small (1536d), cosine
  index: 12 documents, 3,129 pages, 22,832 chunks
  gold set: 25 questions, 31 evidence passages, 0 unfindable

metric                    @1       @3       @5      @10
Document Recall        92.0%   100.0%   100.0%   100.0%
Any Evidence Recall    20.0%    20.0%    24.0%    32.0%
Evidence Coverage      15.0%    15.0%    19.0%    27.0%

By difficulty @5 (doc/any/coverage):
  easy       n=17   100% / 24% / 21%
  medium     n=5    100% / 20% / 20%
  difficult  n=3    100% / 33% /  8%

By gold document @5 (doc/any/coverage):
  ecoplast     n=10  100% / 20% / 12%
  goa_carbon   n=8   100% /  0% /  0%
  infosys      n=7   100% / 57% / 50%

Diagnostic: where retrieval fails the GOLD chunk scores 0.38-0.58 while the
top distractor scores 0.55-0.72 on every question. Weak gold, not strong
distractors — a representation problem, not a K problem.
