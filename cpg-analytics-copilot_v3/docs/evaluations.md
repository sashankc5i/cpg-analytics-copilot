# Evaluations

This document records how quality is measured, what has been observed so far, and what has **not** yet been evaluated.

## 1. Evaluation dimensions
| Dimension | Question | How measured |
|---|---|---|
| Routing | Does a question reach the right governed tool, with valid arguments? | Golden questions (`backend/tests/eval_questions.py`) |
| Grounding | Does every number in an answer appear in tool evidence? | Built-in grounding check; golden run requires zero unverified numbers |
| Analytical validity | Do tools recover effects planted in the synthetic data? | Storyline recovery (section 3) |
| Investigation quality | Are causes ranked sensibly, contradictions found, confidence calibrated? | Manual review against known storylines; no calibration study yet |
| Governance | Are RBAC, scope and audit enforced? | Automated tests |
| Robustness | Graceful behaviour on LLM/tool failure | Automated tests with fake Groq client |
| Usability | Can users complete tasks? | Headless UI walkthrough only; no user study |

## 2. Golden-question routing
Run: `cd backend && python tests/eval_questions.py` (offline planner) or with `GROQ_API_KEY` set to measure the real model.
- **Result (offline planner): 28/28.** Treat this as optimistic: the planner rules were tuned while building this set, so this is a regression check, not an unbiased accuracy estimate.
- **Not yet measured:** Groq routing accuracy, argument accuracy, and tool-choice stability across model versions. This is the most important missing evaluation.
- Defect history from this process: first pass had 1 failure (similar-issue recall raised an error) and 3 mis-routes ("data quality" matched "issue"; "what drove" not recognised; two-entity comparison lacked grouping); a later run exposed a grounding false positive where numbers in a tool's own limitation notes were flagged. All fixed.

## 3. Storyline recovery on synthetic data
The seed plants known effects. Observations from running the engine (values vary slightly by run date):

| Planted effect | Detected? | Evidence observed |
|---|---|---|
| South beverage stockouts (last ~4 weeks) | Yes | `last 4 weeks vs prior`: stockout rate 2.0% → 5.4%; STOCKOUT supported (~35% of a −7.5% / −$51.4K gap); incremental lost sales estimate ≈ $17.9K; South contributes ~50% of the gap; radar's top issue (materiality ≈ 95) |
| Salt & Co promotion ended + post-promo dip | Yes | PROMO supported (~20% of gap) |
| Competitor promo spike in Personal Care | Partly | COMPETITOR unresolved (small estimated effect, correlation weak) — plausible given the planted effect size (−6% units on one category); radar flags Personal Care with market signal |
| Sparkle Detergent +9% list price | Partly verified | Radar flags it as a low-severity price signal (+7.4%). In 4-week investigations the PRICE hypothesis is correctly contradicted because the change predates both windows. Detection inside a 12-week investigation was **not** individually verified |
| Crunch Bites → Crunch Minis cannibalisation | Yes | Promo analysis: Crunch Minis −18.5%, ≈16% of incremental units |
| Missing rows / null discounts / stale feed | Yes | DQ checks and per-result data-quality notes; investigation confidence reduced |
| Normal seasonality | Reported | SEASON unresolved at ~27% — seasonality is a genuine part of the movement |

Typical investigation outcome for "Why did revenue drop in the last 4 weeks?": confidence *medium* (≈61/100), ~45% of the gap unexplained, 4 untestable hypotheses listed as missing evidence.

**Bias found and fixed:** an early lost-sales estimator ignored seasonality, so it attributed a large loss to the *prior* window and nearly cancelled the true effect; replaced by the peer-region baseline (D8 in `decisions.md`).

**Limitations of this evaluation:** ground truth is known only in direction/magnitude by construction; no tolerance bands were set; one random seed; effect sizes were chosen by the author.

## 4. Grounding check characteristics
- Catches: fabricated figures (test: "$999.9M" flagged, "7.5%" verified).
- Misses: wrong attribution of a real number to the wrong entity; correct numbers in wrong context; qualitative claims.
- False positives seen: numbers from static limitation text (fixed by treating tool-supplied text as evidence). Remaining risk: derived numbers an LLM computes (sums, ratios) will be flagged — by design.

## 5. Proposed evaluation program (not yet run)
1. **Routing benchmark:** ≥100 paraphrased questions per tool family, split into tune/hold-out; report tool accuracy, argument exact-match (metric, period, filters), clarification rate, refusal correctness for out-of-scope or restricted requests. Run for each Groq model.
2. **Faithfulness:** sample answers; label each claim as supported/unsupported by cited evidence; target ≥98% supported.
3. **Investigation calibration:** generate many seeded scenarios (vary effect size, noise, combos of causes); measure top-cause recovery rate, false-support rate on null scenarios, and whether confidence correlates with correctness (reliability diagram).
4. **Estimator accuracy:** compare lost-sales, lift and elasticity estimates with known simulation parameters; report bias and interval coverage.
5. **Adversarial/security:** prompt-injection via data values and user text, attempts to access out-of-scope regions, tool-argument fuzzing.
6. **Human evaluation:** analysts rate usefulness and trust on real questions; time-to-answer vs current process.
7. **Latency/cost:** p50/p95 end-to-end latency, tokens per question, tool-call counts (telemetry already records these).

## 6. Acceptance thresholds (proposed)
| Metric | Target |
|---|---|
| Tool routing accuracy (hold-out) | ≥ 90% |
| Argument exact-match | ≥ 85% |
| Unsupported numbers in final answers | < 1% |
| Out-of-scope data returned to scoped users | 0 |
| Null-scenario false "supported" cause rate | < 10% |
| p95 chat latency (Groq) | < 15 s |
