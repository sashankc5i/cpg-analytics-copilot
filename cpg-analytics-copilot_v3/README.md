# CPG Analytics Copilot

React + FastAPI implementation of your *CPG Analytics Copilot – Comprehensive Feature Catalog* (all 94 feature IDs), using **Groq** for language understanding and narration.

**Design principle (TRU-007/008):** the LLM interprets intent and narrates; it never writes SQL and never computes numbers. All figures come from governed, schema-validated, role-checked, row-level-secured analytics tools whose results are stored as numbered evidence (`[E1]`, `[E2]`…). A grounding check flags any number in an answer that cannot be found in tool evidence.

## Quick start

```bash
# Backend (Python 3.11+)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY=...  (optional, see below)
uvicorn app.main:app --reload --port 8000

# Frontend (Node 18+)
cd ../frontend
npm install
npm run dev                   # http://localhost:5173 (proxies /api to :8000)
```

Single-process alternative: run `npm run build` in `frontend/`, then run only the backend; it serves the built app at http://localhost:8000.

The first start creates a synthetic CPG warehouse (`backend/data/cpg.db`, ~75k weekly sales rows over 2 years) with embedded storylines so investigations have real signal to find:
South beverage stockouts, an ended Salt & Co promo with post-promo dip, a Sparkle Detergent price rise, a Personal Care competitor spike, Crunch Bites cannibalising Crunch Minis, and planted data-quality problems (missing rows, null discounts, a stale inventory feed).

**Without `GROQ_API_KEY`** the app still works end to end using a deterministic offline planner (each answer is labelled "offline"). With a key, Groq drives tool selection and narration (`GROQ_MODEL`, default `llama-3.3-70b-versatile`; one automatic retry on `GROQ_FAST_MODEL`, then fallback to the offline planner if Groq is unavailable).

**Demo logins** (password `demo123`): `admin`, `analyst`, `manager`, `exec`, `steward`, `auditor`, and `rm_north` (regional manager restricted by row-level security to the North region; try asking about South).

## Architecture

```
React (Vite)  ->  FastAPI  ->  Agent (Groq tool-calling loop | offline planner)
 chat, pulse       auth/RBAC       | allow-listed tools only, JSON-schema validated
 investigations    audit/telemetry v
 governance, ops               Governed tool registry -> Semantic layer (certified metrics)
                                    |                      parameterised SQL (SQLAlchemy) + row-level scope
                                    v                      pandas calculations
                               Evidence store (SQL, lineage, freshness, DQ, policy per result)
 Investigation engine: plan -> hypotheses -> deterministic tests -> challenge -> confidence -> claims-to-evidence
 State (SQLite): conversations, evidence, investigations, memory, audit, telemetry, metric catalog
```

Backend modules: `analytics/` (core periods + SQL builder, performance, commercial, ops, pulse), `tools.py`, `agent.py`, `investigation.py`, `memory.py`, `security.py`, `governance.py`, `routes.py`.

## Feature coverage

| IDs | Where / how |
|---|---|
| CON-001…003 | `agent.py`: NL questions, multi-turn history, retained context (metric/period/filters/tool) so "and for North?" re-runs the prior analysis |
| CON-004 | `request_clarification` tool, shown as tappable option chips |
| CON-005, 007, 008, 009 | Searchable history; rename/archive/restore; delete cascades to messages, evidence and linked investigations; export conversation (md/json) and investigation (md/html/json) |
| CON-006 | Starter suggestions (from the radar) plus evidence-aware follow-ups after each answer |
| DATA-001…005 | Governed semantic layer + SQL builder (`semantic.py`, `analytics/core.py`): the LLM chooses metric/dimensions/filters via validated tool arguments; SQL is generated from an allow-list and shown in the evidence drawer. Dataset (sales vs inventory) is selected automatically from the metric |
| DATA-006…010 | `compare_periods`, `top_bottom`, `trend_analysis`, `variance_analysis` (prior / prior-year / trailing average + bridge), `drilldown` |
| DATA-011, 012 | `data_quality_check`; every result carries freshness and relevant DQ findings; unequal-length periods are scaled and flagged |
| INV-001…010 | `investigation.py`: plan, catalog + untestable hypotheses (LLM may add extras), ranking on explicit criteria, evidence per test, cross-domain tests (sales/inventory/promo/price/competitor/data), driver decomposition and contribution analysis, summary, replay |
| TRU-001…005 | Contradiction tests (control groups, timing/onset), alternatives, missing evidence, confidence with itemised factors, claims-to-evidence links |
| TRU-006, VIS-003 | Interactive evidence graph (evidence, claims, hypotheses, observation) |
| TRU-007, 008 | LLM never computes or queries; per-role tool allow-list, JSON-schema validation, scope enforcement, telemetry; number-grounding check |
| CPG-001…016 | `performance_scorecard` (product/category/segment/region/channel), `driver_decomposition`, `assortment_analysis`, `customer_cohorts`, `promotion_analysis` (impact/lift/cannibalisation), `stockout_analysis`, `price_volume_mix`, `price_elasticity`, `competitor_signals` |
| PBI-001…007 | Business Pulse: health KPIs, issue radar with materiality score (magnitude/persistence/importance/breadth), cross-domain clustering, event timeline, auto-created investigations ("Scan & auto-investigate" or `RADAR_INTERVAL_MIN`), seasonally-adjusted anomaly detection |
| MEM-001…005 | `memory.py`: issue memory on conclusion, TF-IDF + structural similarity, hypothesis recall, outcome tracking, searchable Knowledge Base (6 clearly labelled seeded examples) |
| VIS-001, 002 | Bar/line/waterfall/forecast-band/timeline charts; collapsible driver tree + price/volume/mix |
| COL-001…003 | Read-only expiring/revocable share links, shares to users, assignment with due date, comments with @mentions and notifications |
| GOV-001 | Local JWT demo auth and OIDC bearer validation via JWKS (`AUTH_MODE=oidc`) with role-claim mapping |
| GOV-002, 003 | RBAC (roles to tools/features); row-level security injected into every query (fails closed for data that cannot be scoped) |
| GOV-004, 005, 006 | Versioned metric catalog (certified/draft/deprecated; deprecated is blocked), audit trail with request IDs, lineage view + per-result lineage |
| OBS-001…005 | `X-Request-ID` correlation, safe JSON errors, structured JSON logs, LLM and tool telemetry (p50/p95 latency, tokens, failures) |
| INT-001…004 | Connector registry; Azure SQL via `ANALYTICS_DB_URL` (SQLAlchemy, portable SQL); BI deep-links; workflow tasks via webhook |
| DEC-001…006 | Recommendations (kept separate from evidence, with assumptions), action tracker, outcome monitoring (recovery %), demand forecast (intervals + holdout MAPE), inventory optimisation (safety stock / reorder point), price optimisation (withheld when elasticity is unreliable) |

## Verification status

- **Tested:** 8 automated tests (`cd backend && pytest tests`) cover auth, RBAC, row-level security, the chat -> investigation -> collaboration -> memory -> delete lifecycle, governance, radar, and the Groq tool-calling loop against a *fake* Groq client (validation feedback, clarification, hallucinated-number flagging, fallback on API failure). All 25 analytics tools were run against the synthetic data, 30 natural-language questions were run through chat, and the React app was driven in headless Chromium with no runtime errors.
- **Not tested:** calls to the real Groq API (no key available in my environment; the loop follows the API's message format, but real model behaviour and tool choice are unverified), a real OIDC provider, and a real Azure SQL database.
- **Data and methods:** the data is synthetic. Estimates such as lost sales, lift, elasticity and forecasts are reasonable but labelled as estimates in each result's limitations; have your analysts validate the methods before decisions rely on them. For Azure SQL, provide `fact_sales`, `fact_inventory`, `fact_promotions`, `fact_competitor`, `fact_cohorts` and `data_sources` tables/views with the columns defined in `backend/app/seed.py`.
- Groq free-tier rate limits are tight for tool-calling; the app sends only role-allowed, keyword-relevant tool schemas to reduce tokens.
