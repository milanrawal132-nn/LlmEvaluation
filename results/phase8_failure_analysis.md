# Phase 8 — failure analysis (chunk_size=600)

75 observations: 3 independent generation runs x 25 questions, using the Phase 7B-accepted configuration.

Groups with 4 or fewer distinct questions are flagged SMALL SAMPLE — one answer changing between runs swings their rate by 30+ points, so treat those rows as leads to check, not findings.

## Overall taxonomy

| label | count | rate |
|---|---|---|
| grounded_correct | 10 | 13.3% |
| generation_failure | 5 | 6.7% |
| generation_refusal | 0 | 0.0% |
| unsupported_correct | 5 | 6.7% |
| retrieval_failure_honest | 48 | 64.0% |
| retrieval_failure_hallucinated | 7 | 9.3% |

## Question type

| group | n_q | n_obs | worst over-represented failure |
|---|---|---|---|
| numeric | 13 | 39 | grounded_correct (15%, 1.2x overall) |
| comparison | 5 | 15 | grounded_correct (20%, 1.5x overall) |
| descriptive **(small sample)** | 4 | 12 | retrieval_failure_hallucinated (25%, 2.7x overall) |
| entity **(small sample)** | 2 | 6 | unsupported_correct (50%, 7.5x overall) |
| date **(small sample)** | 1 | 3 | generation_failure (100%, 15.0x overall) |

## Difficulty

| group | n_q | n_obs | worst over-represented failure |
|---|---|---|---|
| easy | 17 | 51 | unsupported_correct (10%, 1.5x overall) |
| medium | 5 | 15 | grounded_correct (20%, 1.5x overall) |
| difficult **(small sample)** | 3 | 9 | retrieval_failure_hallucinated (33%, 3.6x overall) |

## Document

| group | n_q | n_obs | worst over-represented failure |
|---|---|---|---|
| ecoplast | 10 | 30 | generation_failure (17%, 2.5x overall) |
| goa_carbon | 8 | 24 | retrieval_failure_honest (100%, 1.6x overall) |
| infosys | 7 | 21 | retrieval_failure_hallucinated (33%, 3.6x overall) |
