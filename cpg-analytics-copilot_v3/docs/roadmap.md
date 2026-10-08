# Roadmap

Priorities reflect risk first (verify what exists), then production readiness, then capability. Dates are intentionally omitted; sizes are rough (S ≤ 1 week, M ≈ 2–4 weeks, L > 1 month).

## Phase 0 — Validate what is built (before wider use)
| Item | Why | Size |
|---|---|---|
| Run with a real Groq key; record routing/argument accuracy and fix prompts/tool descriptions | The LLM path is verified only against a fake client | S |
| Expand golden set to ≥100 questions with a hold-out split; add to CI | Current 28 are tuned (optimistic) | S |
| Connect to a real Azure SQL sample and map your schema (views for `fact_*`) | Azure path unverified; schema is assumed | M |
| Test OIDC against your identity provider (role/scope claims) | Enterprise auth unverified | S |
| Analyst review of estimator methods (lost sales, lift, elasticity, forecast) | Estimates are reasonable but unvalidated on real data | M |
| Replace default `JWT_SECRET`, demo users and passwords | Safety | S |

## Phase 1 — Production hardening
- **State store:** move `state.db` to Postgres/Azure SQL; add migrations (Alembic); remove in-process caches or make them shared.
- **Concurrency & performance:** async endpoints or a worker queue for investigations and radar scans; per-user rate limits; query timeouts; result-size caps; caching of repeated tool calls.
- **Streaming UX:** SSE for chat with tool-progress events and token streaming.
- **Security:** secret management, HTTPS/reverse proxy, CORS review, audit/telemetry retention and export, PII review of stored evidence, dependency scanning, prompt-injection tests.
- **Observability:** OpenTelemetry traces, dashboards/alerts on LLM failure rate, p95 latency, tool errors; log shipping.
- **Quality gates in CI:** pytest, golden eval with threshold, frontend build and component tests, Playwright end-to-end.
- **Admin UI:** user/role/scope management (currently seeded/IdP-driven), metric certification workflow with approvals.

## Phase 2 — Analytical depth
- **Data coverage:** daily grain, budget/plan and forecast-vs-actual (true variance vs plan), distribution (numeric/weighted), media spend, supply-chain OTIF, weather/events, price/competitor feeds. These turn today's *untestable* hypotheses (DISTRIBUTION, SUPPLY, MARKETING, EXTERNAL) into testable ones.
- **Better baselines:** seasonality- and trend-adjusted promo baselines, synthetic-control or difference-in-differences for promo/price/stockout effects, hierarchical forecasting with promo/price regressors, prediction-interval calibration.
- **Hypothesis engine:** hypothesis library by business function, learned priors from memory (promote hypotheses that were confirmed in similar past cases), interaction effects, multi-cause attribution that does not double count overlapping explanations.
- **Confidence calibration:** fit confidence scoring to labelled historical investigations instead of hand-set weights.
- **Decision intelligence:** constrained optimisation for inventory (MOQ, pack size, capacity, supplier lead-time variability) and price/promo (competitor reaction, cross-elasticity, margin guardrails); counterfactual "what if we had acted" outcome measurement.
- **Proactive:** scheduled radar with email/Teams notifications, subscriptions per role/scope, de-duplication and re-opening of recurring issues.

## Phase 3 — Product experience
- Saved questions/dashboards, pinned evidence, report/slide export (PDF/PPTX/DOCX), richer sharing (comment-only, per-user permissions).
- Mobile/responsive refinement, accessibility audit, localisation, currency/units configuration.
- In-app explanations of methods (how lift or confidence was computed) linked from each evidence card.
- Feedback loop: thumbs up/down on answers and hypotheses feeding evaluation datasets and memory outcomes.
- Conversation features: attachments, voice, multi-user threads.

## Phase 4 — Platform
- Multi-tenant support; pluggable connectors (Snowflake, BigQuery, Databricks) behind the same governed query layer.
- Pluggable LLM providers with automatic evaluation-based model routing and cost controls.
- Semantic-layer editor and import from existing BI semantic models (e.g. Power BI datasets).
- Workflow integrations beyond webhook (Jira, ServiceNow, Teams, ADO) with two-way status sync.

## Known gaps carried from v1
| Gap | Planned in |
|---|---|
| SQLite state, single instance | Phase 1 |
| Synchronous LLM/tool execution | Phase 1 |
| Untested Groq/OIDC/Azure paths | Phase 0 |
| Heuristic grounding check (numbers only) | Phase 1–2 (claim-level verification) |
| Hand-set scoring/confidence weights | Phase 2 |
| Seeded (not real) institutional memory | Ongoing as real investigations are concluded |
| Offline planner is single-tool and phrase-tuned | Superseded by evaluated LLM routing (Phase 0) |
| Weekly grain only | Phase 2 |
| No frontend automated tests | Phase 1 |

## Success measures
Adoption (weekly active analysts/managers), share of answers with all numbers grounded, investigation time vs manual baseline, % of investigations concluded with an action and recorded outcome, proactive-issue precision (accepted vs dismissed), and LLM failure/latency SLOs.
