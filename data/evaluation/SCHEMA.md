# Gold set schema

Three files. Two are hand-curated and verified; one is derived and must never
be hand-edited.

```
questions.csv       hand-written, verified   25 rows
evidence.csv        hand-written, verified   35 rows in 30 groups
evidence_spans.csv  DERIVED — regenerate with scripts/derive_gold_spans.py
```

## questions.csv

| column | meaning |
|---|---|
| `question_id` | `q001`… |
| `question` | asked verbatim of the pipeline |
| `reference_answer` | human-written; the correctness judge compares against this |
| `difficulty` | `easy` / `medium` / `difficult` |
| `question_type` | `numeric`, `entity`, `date`, `list`, `comparison`, `descriptive` |
| `evidence_mode` | how the question's required **groups** combine |

`evidence_mode` is `all` (every group required) or `any` (any one group
suffices). It is a property of the question, not of any passage.

## evidence.csv

| column | meaning |
|---|---|
| `evidence_id` | `e001`… one row = one *location* |
| `question_id` | owning question |
| `group_id` | one required **fact** |
| `relevant_document` | source PDF |
| `relevant_pages` | verified page(s); also disambiguates duplicates |
| `evidence_text` | verbatim from the extracted text |

**Rows sharing a `group_id` are alternative locations of the same fact, each
independently sufficient. Different groups are different facts, all required
(subject to `evidence_mode`).**

## evidence_spans.csv (derived)

Adds `start_char` / `end_char`: the fact's fixed character range in the source
document, where the source document is `"\n".join(extracted_pages)` —
`src.ingestion.source_text()`. Regenerate after any change to `evidence.csv`
or after re-extracting a PDF.

Never type an offset by hand. Offsets are a mechanical consequence of the
verified `evidence_text`; a typed one is unverifiable and rots silently.

---

# Refinement log

## R1 — one-to-many evidence (Phase 3)

Originally one `evidence_text` per question. q010 needs four segment revenues,
and a single snippet could only ever prove one of them, so evidence became a
separate one-to-many table.

## R2 — `evidence_mode` (before Phase 5)

Coverage treated every row as required. q019's EPS appears in the ratios table
*and* the consolidated statement; retrieving either answers the question in
full, but coverage read 0.5. Added `evidence_mode` on the question.

## R3 — snippet repair for findability (Phase 5)

Five snippets sat inside no chunk at 500/50 — longer than the overlap and
landing on a seam, so their questions could never score full coverage no
matter how good retrieval was. Trimmed to the shortest span still carrying the
asserted fact; q021 and q008 were **split** rather than trimmed, because each
asked for two facts separated by a chunk boundary.

Rule discovered here: with `overlap = 50`, a snippet is *guaranteed* findable
only if it is **≤ 51 characters** (`chunk_size − stride + 1`). Everything
longer is luck that depends on where seams fall.

## R4 — gold source spans (preparing Phase 7A)

Text-substring matching cannot compare chunk sizes, because the ruler changes
shape with the thing it measures:

```
 chunk_size   unfindable snippets (text)   unreachable groups (spans)
        300                            6                            0
        500                            0  <-- baseline               0
        600                            4                            0
       1000                            1                            0
```

At 300, e028 (369 chars) cannot fit in a 300-char chunk at any position. And
the 500 baseline is the only configuration whose gold set was *repaired
against it*, so a text-based comparison would be rigged in its favour.

Spans fix this: a character range does not move when seams do. Coverage is
computed against the **union** of retrieved chunks, so a fact split across two
adjacent chunks scores 1.0 — which is what the model actually saw.

## R5 — evidence groups (preparing Phase 7A)

The span uniqueness check surfaced a real defect: q010's four snippets each
appear **verbatim twice** in the Ecoplast report — p.43 (Directors' Report)
and p.70 (MD&A). A single fixed span would have marked the p.43 copy as a
miss purely because a human happened to verify p.70. That measures the
annotator, not the retriever.

Groups separate *what must be found* from *where it may be found*:

```
question ──evidence_mode──▶ groups (required facts)
                                │
                                └── max ──▶ alternatives (valid locations)
```

- **within a group**: `max` over alternatives. A duplicate is not extra
  evidence, and averaging would penalise retrieval for not finding a second
  copy of something it already has.
- **across groups**: `evidence_mode`. `all` → mean, `any` → max.

Applied: q010 → 4 groups × 2 alternatives (p.43, p.70). q019 → 1 group with
2 alternatives. q008 and q021 → 2 groups each (genuinely different facts, both
required). All others → 1 group, 1 alternative.

### Known consequence for the frozen Phase 5 baseline

The frozen text-based metric asks "is the snippet in *some* chunk", never
"which copy", so a p.43 chunk already counted as a hit for q010. It is
therefore slightly **loose** on that question.

**This is recorded, not corrected.** The Phase 5 baseline stays frozen exactly
as measured; Phase 7A reports span metrics as primary and the text metrics as
secondary diagnostics alongside their per-configuration unfindable counts.
