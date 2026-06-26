# Discovery Document

> Answers the four assignment questions: the reasoning behind what was chosen and what was left
> out, not an idea dump.

**TL;DR**

- Foundation is a deterministic analytics layer (plain SQL, not AI): revenue, margin and
  footfall per shop, category margin in dollars, baristas benchmarked within their shop,
  shop-level ratings.
- One AI feature worth building: classify negative reviews (1-3 stars) into themes. Real signal
  exists (Riverside has a milk-quality cluster, avg rating 3.21).
- Prioritized first by a hard gate (is the answer actually in the text), then by margin dollars
  protected.
- Deliberately NOT built with AI: inferring the cause of a sales trend. The Campus decline has
  no cause in the data, so a model would invent one.

---

## Context: the deterministic foundation (not an AI opportunity)

Plain SQL over the existing tables, built before any model. It answers the WHAT, never the WHY,
and is the substrate the AI reads from:

- **Shop/chain:** revenue, COGS, gross margin ($ and %), tx, avg ticket, items/tx, change vs the
  previous equal-length period.
- **Category:** units, revenue, margin, ranked by **absolute margin dollars** (not %).
- **Barista:** avg ticket, items/tx, pastry attach, benchmarked **within their own shop**.
- **Shop:** avg rating and review count (reviews carry only a shop id, so a rating cannot be
  pinned to a category or barista).

Two principles for every AI feature below:

1. **Prioritize by absolute margin dollars, per period, never hardcoded.** Tea has the highest
   margin % but a fraction of coffee's dollars, so it ranks below.
2. **Cause is out of scope here.** The layer shows that a shop is declining, not why.

The change is period-over-period; with one year of data there is no year-over-year yet. YoY
would control for seasonality by construction and is the obvious addition once a second year
lands.

### Worked example: the Campus decline, and where deterministic analysis stops

Campus is flagged at about -10%, and it is Campus-specific (other shops are down only 3-5% on
shared seasonality). Following it down:

Footfall falls (transactions/day ~29 to ~21, average ticket holds) -> ratings stay stable (avg
3.87, in line with the chain) -> no single complaint theme -> the cause is external (term
calendar, a competitor, construction) -> so it is not in the dataset.

A model asked "why did Campus decline" can only invent a story. The honest output is the
mechanism (footfall, not basket) plus a named list of the data we would need to find the cause.
Same trap: October reads low only because of a chain-wide one-week dip on 2025-10-20 to 26, not
Campus.

---

## 1. AI-driven opportunities

**Opp1, classify negative reviews (1-3 stars).** Reads `reviews.text` + `rating`, assigns a
theme (milk, wait, noise, accuracy, pricing, staff), groups by shop and window. The dashboard
shows reviews verbatim but cannot tell a dozen complaints are one problem. Real instance:
Riverside, lowest avg rating (3.21), ~13 spoiled-milk reviews Oct-Dec 2025. Value: scattered low
ratings become one named, countable issue. (Future: same on 4-5 star reviews to find what to
protect.)

**Opp2, correlate themes with margin-weighted categories.** Maps Opp1 themes onto categories,
ranks where to act by the category's absolute margin dollars. Points to the complaint that
protects the most profit. Depends on Opp1; the ranking itself stays deterministic.

**Opp3, natural-language query over the analytics layer (text-to-SQL).** The owner asks "which
shop lost the most margin last quarter" in plain English; the model writes read-only SQL against
the existing tables and the DB returns the numbers. This is the canonical "make the dashboard
answer questions" feature, and it is genuinely AI. But it is a capability and access feature, not
signal extraction: it surfaces numbers the deterministic layer already computes, faster, rather
than reading something nothing else can read. So it does not clear the "signal actually present"
gate and is judged on reliability and UX instead. Real value, deliberately ranked last (see
section 2), not declined.

---

## 2. Prioritization

| Criterion | Why | Weight |
|---|---|---|
| Signal actually present | Real only where the text carries the answer (Riverside), not where the cause is absent (Campus). Filters hallucination-bait first. | gate |
| Margin dollars protected | Effort follows profit at risk, absolute margin per period. | high |
| Dependency order | Opp2 needs Opp1's labels first. | high |
| Failure blast radius | A wrong label is cheap and visible; a wrong inferred cause drives a wrong decision. | medium |

Ranked: **Opp1** (passes the gate, dependency for everything downstream, this is the Part 2
feature) > **Opp2** (blocked on Opp1, its ranking half is deterministic) > **Opp3** (real AI
feature, but a capability play not signal extraction, so it does not clear the gate; judged on
reliability and UX instead).

---

## 3. Architectural sketch of the top 3

**Top 1, classify reviews.** AI touches one step only: review text -> theme label. Selecting the
1-3 star reviews and all aggregation and ranking after it is deterministic SQL, so the headline
numbers stay reproducible. Data: `reviews.text/rating/shop_id/ts`, nothing new. Cache by review
id (reviews are immutable, never classified twice). Guardrails: closed theme set + explicit
`unknown`, structured output validated against the set, hard scope limit so it never infers why
sales moved.

**Top 2, correlate themes with categories.** Reuses the cached labels, no new model calls.
Theme-to-category is a small fixed table; the ranking is the existing margin computation.

**Top 3, natural-language query (text-to-SQL).** The model translates a plain-English question
into SQL; everything else is the existing read-only analytics layer. Model writes the query, the
DB computes every number. Guardrails: read-only role, generated SQL validated against a
whitelist (no writes, no schema changes), the query shown to the user for transparency, and a
"could not answer" fallback rather than a guessed result. Heavier to make reliable than Opp1,
which is why it sits third.

---

## 4. What I would deliberately NOT build with AI

**Inferring the cause of a sales trend.** Feed the numbers (a shop's decline, its category mix,
its barista stats) to an LLM and ask why. The cause is often not in the data (Campus above), and
a model always returns a fluent answer, so absence of evidence comes back as a plausible story
("students left for summer", except the drop runs through autumn and winter). The boundary: AI
reads signal that exists in the text (the Riverside milk cluster); it does not manufacture
signal that is absent from the data.
