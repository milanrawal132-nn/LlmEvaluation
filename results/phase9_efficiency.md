# Phase 9 — cost, latency, and efficiency analysis

Pricing verified 2026-08-15: gpt-4o-mini $0.15/1M input, $0.6/1M output. Source: https://platform.openai.com/docs/pricing (OpenAI official); cross-checked via web search, Aug 2026

Retrieval query latency was not captured during Phase 7A and is not reported here.

## Index efficiency (Phase 7A, not rebuilt)

| metric | 500 | 600 | abs diff | pct diff |
|---|---|---|---|---|
| chunk_count | 22832 | 18682 | -4150.0 | -18.2% |
| index_size_mb | 259.1 | 222.9 | -36.2 | -14.0% |
| build_time_seconds | 552.9 | 491.7 | -61.2 | -11.1% |

## Token / latency / cost per configuration

| chunk_size | mean input tok | mean output tok | mean latency (s) | total cost | cost/correct | cost/grounded_correct |
|---|---|---|---|---|---|---|
| 500 | 847.4 | 17.4 | 1.10 | $0.0103 | $0.00129 | $0.00129 |
| 600 | 998.7 | 17.0 | 1.05 | $0.0120 | $0.00080 | $0.00120 |
