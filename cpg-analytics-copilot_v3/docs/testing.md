# Testing

## 1. Running the tests
```bash
cd backend
pip install -r requirements.txt
python -m pytest tests -q            # 8 tests, ~7-10 s, no network, temp databases
python tests/eval_questions.py       # golden-question routing evaluation (offline planner)
GROQ_API_KEY=... python tests/eval_questions.py   # same, against real Groq
```
Tests create temporary SQLite databases (`STATE_DB`, `ANALYTICS_DB_URL` set to a temp dir) and force `GROQ_API_KEY=""`, so they never touch `backend/data/` and never call external services. The synthetic dataset is regenerated per run relative to today's date.

## 2. Automated test inventory
### `tests/test_api.py` (integration, FastAPI TestClient, offline planner)
| Test | What it proves |
|---|---|
| `test_auth_and_request_id` | Bad login → 401; unauthenticated call returns `request_id` and `X-Request-ID`; valid login works |
| `test_chat_flow_and_conversation_lifecycle` | Question → evidence + suggestions + `[E1]`; evidence endpoint returns SQL and freshness; follow-up in same conversation; rename + archive + list archived; export; ambiguous message → clarification options |
| `test_investigation_end_to_end` | Chat "why" starts an investigation; STOCKOUT supported; challenge, confidence factors, replay, graph, driver tree, export; assign, @mention notification, share link → public view → revoke; action done → outcome monitor; conclude → memory; workflow task; **deleting the conversation cascades to the investigation** |
| `test_rbac_and_row_level_security` | `exec` blocked from `price_optimization`; North-scoped manager only sees North and is blocked from South; non-auditor blocked from audit, auditor allowed |
| `test_governance_pulse_and_ops` | Metric edit bumps version; deprecated metric blocked, then restored; radar scan auto-creates investigations; overview KPIs; telemetry counts; integrations; lineage; data-quality tool |

### `tests/test_llm_loop.py` (Groq loop with a fake client)
| Test | What it proves |
|---|---|
| `test_tool_loop_grounding_and_telemetry` | Tool call executed and result fed back as a `tool` message; system prompt contains the no-compute rule; allowed tool schemas sent; fabricated "$999.9M" flagged while real "7.5%" verified; LLM telemetry recorded |
| `test_validation_error_is_fed_back_and_clarification` | Invalid region → validation error with valid values returned to the model; `request_clarification` produces option chips |
| `test_llm_failure_falls_back_to_offline` | API exception (rate limit) → offline planner still answers; failure counted in telemetry |

### `tests/eval_questions.py` (not collected by pytest)
28 golden questions → expected tool(s), tool success and zero unverified numbers. Currently 28/28 offline (optimistic; see `evaluations.md`).

## 3. Manual / exploratory checks performed
- All 23 analytic tools executed directly against the synthetic data (shape of results, errors, timings: individual tools returned quickly; investigations take several seconds).
- 30 natural-language questions through chat (routing, follow-ups, ambiguity).
- Headless Chromium walkthrough: login → ask "Why did revenue drop…" → open investigation → every tab → evidence drawer → Pulse, Investigations, Knowledge, Governance, Operations. Result: no page errors. The only console errors were blocked Google Fonts in the sandbox.
- Screenshots reviewed for chat, investigation summary, evidence graph and Business Pulse.

## 4. Manual UI regression checklist
1. Sign in as `manager`; ask "Which regions declined the most last month?" → evidence card, chart, data table, freshness/DQ chips; click `E1` → drawer tabs (Data, SQL, Lineage, Quality).
2. Ask "and for Beverages?" → follow-up reuses prior analysis.
3. Ask "hmm" → clarification chips.
4. Ask "Why did revenue drop in the last 4 weeks?" → investigation card; open it; check Hypotheses (expand criteria), Challenge, Drivers, Graph (click nodes), Replay (play), Team (assign `analyst`, comment `@analyst`, add/complete action, record outcome, Monitor recovery, share link, workflow task).
5. Sign in as `analyst` → notification for the mention; open shared link in a private window (no login).
6. Sign in as `rm_north` → ask about South → policy message; Pulse shows only North-scoped issues.
7. Sign in as `steward` → edit a metric; confirm version increments; deprecate → queries using it fail with a clear message; restore.
8. Sign in as `auditor` → Governance → Audit trail lists the actions above with request IDs.
9. Rename, archive, restore, delete a conversation (delete warns and removes linked investigations).
10. Operations → Test data connection, stale-feed flag on inventory, telemetry (admin only).

## 5. Testing with a real Groq key
1. Set `GROQ_API_KEY` in `backend/.env` and start the backend; the login page shows "Groq · <model>".
2. Run `python tests/eval_questions.py` with the key and record routing accuracy.
3. Watch `/api/admin/telemetry` for failures, rate limits and token use; logs are JSON on stdout (search by `request_id`).
4. Specifically try: multi-step questions, ambiguous ones, requests for numbers the tools cannot supply, and prompt-injection text inside a question.

## 6. Coverage gaps (known)
- No tests against a real Groq model, OIDC provider or Azure SQL.
- No frontend unit/component tests or automated end-to-end browser tests (the walkthrough script was ad hoc and not shipped).
- No load, concurrency or SQLite-locking tests; no security fuzzing or dependency scanning.
- Statistical methods are tested for execution and plausibility on one seed, not for accuracy across seeds (see `evaluations.md`).
- Time-dependent behaviour (month boundaries, year rollover) relies on the seed being generated relative to today; no frozen-clock tests.

## 7. Suggested CI
`pytest` on every push; nightly `eval_questions.py` with a Groq key and a stored baseline; `npm run build` for the frontend; dependency audit (`pip-audit`, `npm audit`).
