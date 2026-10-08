# Agent Design

## 1. Goals
Give business users natural-language access to analytics **without** letting a language model fabricate numbers, write SQL or bypass access controls.

## 2. Roles of the LLM
| Used for | Not used for |
|---|---|
| Understanding the question; choosing a tool and arguments | Computing, estimating or recalling numbers |
| Asking one clarifying question | Writing SQL or touching the database |
| Narrating results with evidence citations | Deciding permissions or data scope |
| Proposing up to 2 extra *untestable* hypotheses | Ranking, scoring or confidence of hypotheses |
| Executive narrative of an investigation (facts passed in) | Producing the claims list (built deterministically) |

## 3. Conversation loop (`agent.py`)
```
user message
  -> load history (8 msgs) + context {last_tool,last_metric,last_period,last_filters,last_args,last_investigation_id}
  -> Groq (tools = role-allowed + keyword subset)
        tool_call? -> Turn.call -> tools.execute -> evidence E{n} -> compact JSON back to model
        (max 6 rounds; request_clarification ends the turn; start_investigation runs the engine)
  -> final text -> ensure [E#] -> grounding check -> suggestions -> persist -> audit
```
### System prompt rules (summarised)
1. Never compute or recall numbers; call tools. 2. Cite `[E#]` after claims. 3. Clarify only when ambiguity changes the analysis; otherwise default (revenue, last_4_weeks) and say so. 4. "Why/root cause" → `start_investigation`. 5. Report limitations from tool results. 6. Be concise. 7. Correct tool errors once; relay policy errors plainly.
The prompt also includes the latest data week, valid metric/dimension/product values, the user's role and scope, and the retained context for follow-ups.

## 4. Tools
26 registered tools: 23 analytic, plus `recall_similar_issues`, `start_investigation`, `request_clarification` (handled inside the agent).

| Tier | Tools |
|---|---|
| core | query_metric, compare_periods, top_bottom, trend_analysis, variance_analysis, drilldown, performance_scorecard, driver_decomposition, price_volume_mix, anomaly_detection, business_health_overview, detect_business_issues, business_timeline, data_quality_check, recall_similar_issues, start_investigation, request_clarification |
| advanced | promotion_analysis (impact/lift/cannibalization), stockout_analysis, assortment_analysis, customer_cohorts, competitor_signals, price_elasticity |
| decision | demand_forecast, inventory_optimization, price_optimization |

**Execution pipeline (`tools.execute`):** known tool → role permits tool → drop unknown args and coerce types (string→list/number/object) → JSON-schema validation → `Ctx(scope)` → function → metadata → telemetry. Errors return `{error, kind}` (`validation`, `policy`, `internal`); validation errors list valid values so the model can self-correct. Internal errors never leak details.

**Tool subset:** to reduce tokens, only core-always tools plus tools whose keywords appear in the message/recent history are sent (`openai_tools`).

**Result contract:** `{headline, rows, chart, facts, limitations, warnings, meta{sql, params, tables, periods, filters, policy, freshness, data_quality, lineage, runtime_ms}}`.

## 5. Evidence and grounding
- Every successful call becomes `evidence(owner_type, owner_id, label)`; conversation labels (`E1…`) and investigation labels are separate namespaces. Chat answers that embed an investigation strip `[E#]` and point to the investigation.
- **Grounding check:** numbers in the final answer (with K/M/% handling) must match any number in tool rows/facts/headlines within max(0.06, 2%). Years and integers ≤12 without a suffix/decimal are ignored. Unmatched numbers are listed in the UI as "not found in tool evidence".

## 6. Offline planner
Deterministic fallback when no key or both Groq attempts fail. `nlu.parse` extracts metric, period, comparison, filters (exact names + synonyms) and group-by; `offline_plan` maps keywords to a single tool in priority order (quality → investigate → radar/health → anomaly → forecast → … → compare → query). Follow-ups ("and for North?") re-run the last tool with replaced filters/period. Anything ambiguous returns a clarification with options.

## 7. Investigation engine (`investigation.py`)
1. **Observation:** `compare_periods` gives the gap G (units/revenue only). Prior period is scaled when week counts differ.
2. **Timing baseline:** metric onset week via `onset()` (≥1σ for 2 consecutive weeks vs an 8-week baseline).
3. **Hypothesis tests** (each uses governed tools; contributes evidence):
   - *Causes:* STOCKOUT, PROMO (ended/lower support, post-promo dip), PRICE (list price ≥3% with excess volume loss vs control), MIX, COMPETITOR, CANNIBAL, SEASON (same weeks prior year), DATAQ.
   - *Localisation:* WHERE_region / channel / segment / product (supported if top member ≥40% of gap and ≥1.5× its revenue share).
   - *Untestable:* DISTRIBUTION, SUPPLY, MARKETING, EXTERNAL (+ up to 2 LLM-proposed) with the data needed.
4. **Scoring:** `score = 0.45·materiality + 0.25·strength + 0.20·consistency + 0.10·coverage`. A "supported" status with score < 0.35 is downgraded to "unresolved". Untestable scores 0.
5. **Challenge (leading supported cause):** contradictions (control-group differential, onset timing, <60% explained), alternatives, overlap note, missing evidence (untestable hypotheses, data-quality findings, ignored-filter warnings).
6. **Confidence:** `40 + 40·min(1, Σ supported explained%) + 10·coverage − 8·contradictions − 4·DQ findings (−15 if no supported cause)`, clipped 5–95; ≥70 high, ≥45 medium, else low. Factors are listed in the UI.
7. **Claims → evidence:** deterministic claims (finding/caveat) each linked to evidence labels; the LLM narrative (optional) may only restate them.
8. **Recommendations:** per supported cause, with rationale, evidence, assumptions and expected impact, kept separate from findings.
9. **Artifacts:** evidence graph, replay log, driver tree (from `driver_decomposition` evidence), similar issues and hypothesis recall.

## 8. Radar and materiality (`analytics/pulse.py`)
Signals: revenue anomalies (dimensions + region×category), stockout spikes (≥8pp and ≥15% of days), ended promos, list-price rises (≥5%), competitor promo spikes (≥0.25). Score per signal `100·(0.4·magnitude + 0.25·persistence + 0.2·importance)`; cluster score adds up to 15 for domain breadth. Severity: high ≥60, medium ≥35. Auto-investigation threshold `AUTO_INVESTIGATE_THRESHOLD` (default 60).

## 9. Failure behaviour
| Failure | Behaviour |
|---|---|
| Groq error / rate limit | Retry once on fast model, then offline planner; logged and counted in telemetry |
| Invalid tool args | Error with valid values returned to model for one correction |
| Policy denial | Plain message to the user; audit row |
| No data in scope | Tool error explaining the unavailable evidence |
| Unexpected exception | Generic message + request ID; details only in logs |

## 10. Extending
Add a tool: write the function returning the result contract, register a `Tool` in `tools.py` with a schema and tier, add it to the role lists in `security.py`, add keywords for subset selection, and (optionally) a rule in `offline_plan`.
