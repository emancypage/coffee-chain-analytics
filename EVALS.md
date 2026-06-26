# EVALS

How I would measure the production quality of the review-theme classifier if it shipped tomorrow.

## What is being evaluated

A single-label classifier: one negative review (rating <= 2) to one theme from a closed set
(`dairy`, `wait_time`, `noise`, `order_accuracy`, `pricing`, `staff`, `wifi`, `seating`,
`other`, `unknown`). Everything downstream (counting, grouping, ranking per shop) is
deterministic SQL and does not need model evaluation. The only thing to measure is the label.

## Dataset

A hand-labelled gold set that would live in the repo at `evals/gold.jsonl` (`review_id`, `theme`).
Build it by stratified sampling across shops and ratings so every theme and every shop is
represented, then label by hand. Two passes with adjudication on disagreements; record the
ambiguous ones, they are the cases that move scores. Deliberately include the hard inputs:
paraphrased dairy ("latte was sour", "milk seemed off"), mixed reviews that pair a guess about
the business with a real complaint, vague text that should land on `unknown`, and real
complaints with no named theme that should land on `other`. A few hundred labels is enough for
stable per-theme numbers on this data size.

## Metrics

- Per-theme precision, recall, F1, and macro-F1 across themes (macro so rare themes are not
  drowned by the common ones).
- Headline metric: recall on operational-cluster themes, `dairy` first. Missing a real cluster
  is the expensive error, an owner stays blind to a spoiling-milk problem for weeks.
- `unknown` and `other` rate as a health signal. A spike means the taxonomy is drifting or the
  prompt regressed, even before labels are available.
- No-cluster check (the hallucination guard as a number): on a shop known to be scattered
  (Campus), measure the false-cluster rate, whether the pipeline reports a concentration that is
  not there. The endpoint test `test_campus_has_no_dominant_complaint_cluster` is the seed of
  this check.
- Confidence calibration: bucket model confidence against observed accuracy, so the score is
  trustworthy enough to threshold on later.

## Catching regressions when the model or prompt changes

The prompt is a versioned file and the cache is keyed by `(review_id, model, prompt_version)`,
so bumping either forces a clean reclassification rather than mixing label generations. On a
change:

1. Reclassify the gold set with the new model or prompt version.
2. Compare macro-F1 and per-theme F1 against the committed baseline. Fail the change if macro-F1
   drops beyond a set margin or if `dairy` recall drops at all.
3. Diff the label distribution against the previous version (population stability). A large shift
   flags drift even on reviews that are not in the gold set.

In production, monitor the `unknown`/`other` rate, the label distribution, p50/p95 latency, and
daily cost. Sample-audit low-confidence and `other` labels on a schedule and fold the
corrections back into the gold set so it grows with the real traffic.

## Model, cost, latency

Model: `gpt-4o-mini` through an OpenAI-compatible API (configurable via `OPENAI_BASE_URL`, so
the same code runs against OpenRouter or a local Ollama server). It is strong enough for
constrained single-label classification with JSON output, and the cheapest tier that is.

Cost is about $0.0001 per review classified (roughly 450 input plus 30 output tokens at
gpt-4o-mini rates), so the 45 negative reviews cost under one cent. Latency is sub-second to
about two seconds per call. Classification is an offline batch cached by review id, so the cost
is paid once per (review, prompt version) and never sits on the dashboard request path.
