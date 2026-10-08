# Design Decisions

Format: context → decision → consequences. Status is *Accepted* unless noted.

### D1. The LLM never writes SQL or computes numbers
**Context:** Catalog items DATA-002, TRU-007, TRU-008 require trustworthy, auditable numbers. LLM-generated SQL risks wrong joins, unsafe queries and unreproducible answers.
**Decision:** The model only chooses a tool and validated arguments. SQL is built from allow-listed identifiers with bind parameters; calculations run in pandas.
**Consequences:** Every number is reproducible and inspectable (SQL, params, lineage shown). Flexibility is bounded by the tool set; a new question type needs a new tool or parameter. "NL to SQL" is satisfied as "NL to a controlled query specification".

### D2. Evidence-first answers with a grounding check
Each tool result is stored as numbered evidence; answers cite `[E#]`; numbers are verified against evidence (±2%). **Consequence:** hallucinated numbers are flagged, not blocked; the check is heuristic (e.g. it ignores small integers and years) and tool-text numbers are treated as evidence.

### D3. Offline planner alongside Groq
**Context:** Needs to run locally without a key, and survive Groq rate limits.
**Decision:** Deterministic keyword planner reusing the same governed tool path; automatic fallback when Groq fails twice.
**Consequences:** Always-available demo and graceful degradation. Offline routing is a single tool per question and is tuned to known phrasings; it is not a substitute for the LLM on complex questions.

### D4. Keyword-based tool subsetting
Sending all 26 tool schemas costs thousands of tokens per call and strains Groq free-tier limits. Only core tools plus tools matching message keywords are sent. **Risk:** a relevant tool could be omitted for unusual phrasing; core tools plus `start_investigation` and clarification remain available.

### D5. Deterministic investigation tests; LLM only narrates
Hypothesis status, scoring, contradictions and confidence are computed from tool facts, with explicit weights (0.45/0.25/0.20/0.10). The LLM may add *untestable* hypotheses and write the narrative but cannot change statuses. **Consequence:** reproducible, explainable ranking; weights are judgement calls, not fitted.

### D6. "Where" is separated from "why"
Concentration findings (region/channel/segment/product) are *localisation* hypotheses, excluded from the cause ranking, because "South contributes 50% of the gap" is a description, not a cause.

### D7. Contradictions are first-class
The leading cause is challenged with control-group comparisons (affected vs unaffected product-regions), onset-timing checks, and "explains <60%" flags; confidence is penalised per contradiction. Statuses can be downgraded when score <0.35.

### D8. Estimators chosen for robustness over sophistication
- **Lost sales from stockouts:** peer-region baseline (historic share × same-week units of unaffected regions). The first version (trailing non-stockout mean) was biased by seasonality and inflated prior-period loss, so it was replaced. Falls back to the trailing mean when fewer than 3 regions are in scope.
- **Promo lift:** mean of the 4 pre-promo weeks; no seasonality removal (stated limitation).
- **Elasticity:** log-log OLS with promo, stockout, seasonality and trend controls; optimisation is withheld when the interval spans zero.
- **Forecast:** log-linear trend + two annual harmonics with 8-week holdout MAPE; chosen for transparency over ML accuracy.

### D9. Weekly grain; periods assigned by week-start date
Simple, portable and matches typical CPG syndicated/retail calendars. Calendar words ("last month") are relative to the latest data date. Unequal-length comparisons scale the comparison side (and warn) instead of silently comparing 4 vs 5 weeks. A bug where week-based "prior period" was one week short was found and fixed during testing.

### D10. Row-level security enforced in the query layer, failing closed
Scope filters are merged into every query inside `core.fetch`. Data that cannot be scoped (inventory by channel/segment; cohorts by region) is denied. Radar results are persisted per scope hash, and investigations are visible only if created under an equal-or-narrower scope.

### D11. SQLite for local state and demo analytics; SQLAlchemy for analytics portability
**Decision:** state in plain `sqlite3`; analytics through SQLAlchemy so `ANALYTICS_DB_URL` can point to Azure SQL. SQL is limited to portable constructs.
**Consequences:** zero-setup local use. Not verified against Azure SQL; the state DB would need replacing for multi-instance deployment.

### D12. Synthetic data with embedded storylines
Lets investigations, radar and memory be demonstrated and tested with known ground truth. **Consequence:** results validate the machinery, not your business; seeded memory records are labelled "historical (seeded example)".

### D13. Local JWT auth plus OIDC mode
Demo users with PBKDF2 hashes for local use; `AUTH_MODE=oidc` validates RS256 bearer tokens via JWKS and maps role claims. **Not verified** against a real IdP. Default `JWT_SECRET` and demo password must be changed outside local use.

### D14. Evidence labels are scoped to their owner
Conversation and investigation both use `E1…`. Investigation labels would be wrong inside chat, so chat strips them when an investigation is embedded and links to the investigation instead.

### D15. Recommendations are separate from findings
Each recommendation lists rationale, evidence, assumptions and expected impact, and is rendered apart from evidence (DEC-001). Recommendations are advisory text templates keyed to supported causes, not optimisation output.

### D16. Metric governance protects definitions, not formulas
Stewards can edit descriptions, owners and status (versioned, audited); formulas live in code so changes go through review. Deprecated metrics are blocked at execution.

### D17. Deletion cascades and audit retention
Deleting a conversation removes its evidence and the investigations created from it (CON-008). Audit rows are retained and record the deletion. Telemetry and audit tables have no retention policy yet.

### D18. React without a state library or Tailwind
Plain React + react-router + Recharts + custom CSS keeps the dependency surface small. Data fetching is imperative (`api.js`); caching and optimistic updates are not implemented.

### Rejected alternatives
| Option | Why not |
|---|---|
| LLM-generated SQL with validation | Harder to guarantee correctness/scope; weaker audit story |
| Vector store for memory | Small corpus; TF-IDF + structured similarity is explainable and dependency-free |
| Streaming chat (SSE) in v1 | Tool loops are short; added complexity deferred (see roadmap) |
| Async DB/LLM calls | Sync is simpler for local single-user; revisit with load |
