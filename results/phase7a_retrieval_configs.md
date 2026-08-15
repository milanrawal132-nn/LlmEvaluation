# Phase 7A — retrieval-only chunk-size experiment

Fixed: overlap=50, embedding_model=text-embedding-3-small, distance=cosine, 12-document corpus, gold set = 25 questions / 35 evidence rows / 30 groups. No generation, no judge calls.

## Primary comparison

| chunk_size | K | Document Recall | Gold Span Any Recall | Gold Span Coverage | Legacy Any Recall | Legacy Coverage |
|---|---|---|---|---|---|---|
| 300 | 1 | 92.0% | 16.0% | 14.0% | 16.0% | 14.0% |
| 300 | 3 | 100.0% | 16.0% | 17.3% | 16.0% | 14.0% |
| 300 | 5 | 100.0% | 20.0% | 21.3% | 20.0% | 18.0% |
| 300 | 10 | 100.0% | 20.0% | 21.3% | 20.0% | 18.0% |
| 500 | 1 | 92.0% | 20.0% | 15.7% | 20.0% | 15.0% |
| 500 | 3 | 100.0% | 20.0% | 16.3% | 20.0% | 15.0% |
| 500 | 5 | 100.0% | 24.0% | 19.7% | 24.0% | 19.0% |
| 500 | 10 | 100.0% | 32.0% | 27.7% | 32.0% | 27.0% |
| 600 | 1 | 96.0% | 8.0% | 10.5% | 8.0% | 6.0% |
| 600 | 3 | 100.0% | 12.0% | 18.1% | 12.0% | 11.0% |
| 600 | 5 | 100.0% | 20.0% | 23.9% | 16.0% | 15.0% |
| 600 | 10 | 100.0% | 28.0% | 31.9% | 24.0% | 23.0% |
| 1000 | 1 | 96.0% | 12.0% | 11.3% | 12.0% | 11.0% |
| 1000 | 3 | 100.0% | 12.0% | 11.6% | 12.0% | 11.0% |
| 1000 | 5 | 100.0% | 20.0% | 19.6% | 20.0% | 19.0% |
| 1000 | 10 | 100.0% | 24.0% | 23.6% | 24.0% | 23.0% |

## Build / index diagnostics

| chunk_size | chunk_count | index_size_mb | build_time_s | legacy_unfindable | unreachable_groups | 1-chunk | 2-chunk | 3+-chunk |
|---|---|---|---|---|---|---|---|---|
| 300 | 41093 | 388.3 | 900.9 | 8 | 0 | 24 | 5 | 1 |
| 500 | 22832 | 259.1 | 552.9 | 0 | 0 | 30 | 0 | 0 |
| 600 | 18682 | 222.9 | 491.7 | 5 | 0 | 27 | 3 | 0 |
| 1000 | 10819 | 189.5 | 307.6 | 2 | 0 | 29 | 1 | 0 |

## Selection rule outcome

Winner (pre-registered rule): **600**

Full ranking, best to worst: 600 > 300 > 500 > 1000

