# Coffee Chain Analytics

A small coffee-chain dashboard (5 shops, 12 months of data) with two layers:

- A deterministic analytics layer over the existing tables: revenue, margin and footfall per
  shop, category contribution ranked by absolute margin, barista benchmarks, shop ratings.
  Plain SQL, no model.
- An AI layer that classifies the free text of negative reviews into themes, so a recurring
  problem (for example a milk-quality cluster at one shop) becomes countable.

Part 1 reasoning is in [DISCOVERY.md](DISCOVERY.md). Evaluation strategy is in
[EVALS.md](EVALS.md). The original brief is in [ASSIGNMENT.md](ASSIGNMENT.md).

## How to run

Docker:

```bash
docker compose up
```

Dashboard at http://localhost:8000.

Or locally:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### Populating review themes (the AI feature)

Classification runs offline and is cached. The dashboard reads the cache and never calls the
model on a request. To classify the negative reviews:

```bash
OPENAI_API_KEY=sk-... python -m ai.classify
# inside Docker:
# docker compose exec -e OPENAI_API_KEY=sk-... app python -m ai.classify
```

Then open the "Review Themes" tab. Without a key you can fill the cache with a keyword fallback
to try the surface:

```bash
python -m ai.classify --fake
AI_MODEL=fake-keyword python -m uvicorn main:app   # so the tab reads the fake labels
```

Configuration (environment): `AI_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL` (for
OpenRouter or a local Ollama server), `AI_PROMPT_VERSION` (default `v1`).

## The AI feature

- **Where the model sits:** one step only, review text to a theme label. Selecting the negative
  reviews and all counting, grouping and ranking is deterministic SQL on top of the analytics
  layer, so the numbers on the dashboard stay reproducible.
- **Prompt:** [prompts/review_classifier.v1.md](prompts/review_classifier.v1.md), versioned.
  Output is strict JSON validated against a Pydantic schema (theme, confidence, evidence). JSON
  mode is used instead of a provider-specific structured-output API so the same code runs on
  OpenAI, OpenRouter and Ollama; the closed theme enum plus schema validation keeps the output
  well-formed and is also the main defence against prompt injection through review text.
- **Cache:** a sidecar SQLite file keyed by `(review_id, model, prompt_version)`. coffee.db is
  never written. Bumping the prompt version or the model forces a clean reclassification.

### Edge cases handled

- Empty or whitespace-only review text returns `unknown`, not a forced theme.
- Invalid JSON or a theme outside the set: one retry, then a safe `unknown` fallback.
- A review that speculates about sales or foot traffic: the prompt classifies the concrete
  complaint and ignores the speculation. The classifier never explains a sales trend.
- Prompt-injection text in a review is treated as content, constrained by the enum and schema.
- Reviews not yet classified are reported as a count in the UI, not hidden.

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

- Analytics endpoints: anchors read from the seeded database plus invariants
  (`tests/test_analytics.py`).
- Classifier: schema validation, the keyword fake classifier, and cache hit/miss including
  prompt-version invalidation, offline (`tests/test_classifier.py`).
- LLM classifier path: JSON parse, single retry, unknown fallback, and the empty-text
  short-circuit, with a stubbed client and no network (`tests/test_llm_classifier.py`).
- Review-themes endpoint: Riverside's dairy cluster surfaces, Campus stays scattered (the
  no-cluster guard), coverage is reported, the shop filter works (`tests/test_review_themes.py`).

The end-to-end pipeline (reviews to cache to endpoint to UI) is verified offline with the fake
classifier, and LLMClassifier's parse, retry and fallback logic is covered by the stubbed-client
tests. The only part that needs a key and a network is the actual provider call, run through
`python -m ai.classify`.
