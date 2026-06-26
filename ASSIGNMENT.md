# Coffee Chain Analytics — Take-home Assignment

## Context

You have a working analytics dashboard for a small coffee chain — **5 shops, 12 months of operational data**. Transactions, menu, reviews, staff shifts, shop metadata. The dashboard shows raw tables, numbers, lists. It is deliberately **"dumb"** — it does not summarize, forecast, recommend, or explain anything.

Your job is to show us how you think about turning this into a product that uses AI **where it actually helps**.

---

## Stack (what's already here)

- **Backend:** Python + FastAPI, SQLite
- **Frontend:** single HTML file + vanilla JS, no build step
- **Data:** SQLite database, pre-seeded

You can run it with:

```bash
docker compose up
# or
pip install -r requirements.txt && python -m uvicorn main:app --reload
```

The dashboard is available at `http://localhost:8000`.

---

## What you need to deliver

The task has **two parts**. Part 1 is a document. Part 2 is code + a document. All writing is in **English**.

### Part 1 — Discovery Document (`DISCOVERY.md`, ~2 pages)

Answer these four questions:

1. **What AI-driven opportunities do you see in this application?** List each one with: what it does, what signal / data it uses, what value it gives to the user.
2. **How would you prioritize these opportunities?** Explain your criteria. Pick the top 3.
3. **Architectural sketch of the top 3.** For each: where the AI layer sits, what is deterministic vs model-based, what data is required, where caching / guardrails belong.
4. **What would you deliberately NOT build with AI here, and why?** Be specific about failure modes you want to avoid.

We are not looking for exhaustive idea dumps. We are looking for **the logic behind what you chose, what you didn't, and why**.

### Part 2 — Implementation of one idea (end-to-end)

Pick **one** idea from Part 1 and implement it inside the existing app. Full path — from user-visible surface to the LLM call and back.

Deliver:

- **Working code.** New endpoint(s), UI change, whatever is needed. Single command to run.
- **System prompt** — stored as a versioned file, structured, with your reasoning on format choice.
- **Edge case list** — what inputs break the naive version, how your implementation handles them.
- **Testing approach** — how you tested that the feature works and doesn't regress.
- **`EVALS.md` (~1 page)** — how you would measure production quality of this feature if it shipped tomorrow: what dataset you would build, what metric, how you would catch regressions when the model or prompt changes.
- **Choice of model / provider** — which you used and why. Include a one-sentence note on cost and latency trade-offs.

---

## Rules

- **Any implementation language is allowed.** You can add a separate AI service in Node.js / Go / Python / whatever. Keep the existing Python app or replace parts of it — your call. Just keep it runnable with one command.
- **Any LLM provider is allowed** (Anthropic, OpenAI, local model via Ollama, etc.). Bring your own API key.
- **All documentation is in English.**
- **Git history matters.** We will read your commits. We prefer meaningful small commits over one big "initial commit" dump.
- **We are not evaluating frontend polish.** Make the feature accessible from the UI, but we do not care about visual design.

---

## Time expectation

Up to **1 week** from the moment you start. Realistic focused work: **3-4 hours**. If you spend 30+ hours on this, something went wrong — stop and send what you have with a note explaining your reasoning.

---

## What we evaluate

Roughly, in this order:

1. Range and quality of ideas in Part 1 — do you see where AI fits and where it doesn't?
2. Quality of the prioritization logic — can you defend your choices?
3. Production-grade implementation of one idea — not "playground style"
4. Reasoning about evaluation and regression — can you tell if this AI feature is still working a month after ship?
5. Awareness of failure modes — hallucination, context degradation, cost, latency

---

## How to submit

You have read access to this repository as an outside collaborator.

1. On GitHub, click **"Use this template"** → **"Create a new repository"**. Give it any name. We recommend making it **private** (public is also fine — your call).
2. Clone your new repository locally and work there. All changes — new files, modified files, the AI service, prompts, documentation — go into your repository.
3. Commit as you go. We will read your commit history.
4. Push your commits.
5. If you made your repository **private**, add the recruiter as a collaborator (read access is enough).
6. **Send the recruiter a link to your repository**, e.g. `https://github.com/your-username/your-repo-name`.

Do **not** open a Pull Request against the original repository — we review each submission independently.

Also:

- Make sure the `README.md` at the top of your repository has a clear **"how to run"** section.
- Put your `DISCOVERY.md` and `EVALS.md` at the root of the repository.
- If you used any paid API, mention the provider and an estimate of cost-per-request in `EVALS.md`.

Good luck.
