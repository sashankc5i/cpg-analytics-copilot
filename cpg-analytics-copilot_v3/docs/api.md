# API Reference

Base path `/api`. JSON in/out. Authenticated endpoints need `Authorization: Bearer <token>`.
Every response carries `X-Request-ID`. Errors have the shape `{"error": "message", "request_id": "..."}` with status 400 (validation), 401 (auth), 403 (role/policy), 404, 422 (request body), 500 (internal, no details).
Interactive docs: `/docs` (FastAPI Swagger) when the backend runs.

"Feature" below is the role feature required (see `security.py`): chat, investigate, share, assign, comment, audit_view, metric_admin, telemetry_view, integrations, user_admin, replay, export.

## Auth & metadata
| Method & path | Auth/feature | Description |
|---|---|---|
| GET `/health` | public | Status, LLM mode (`groq`/`offline`), model |
| POST `/auth/login` | public | `{username,password}` → `{token,user}` (local mode) |
| GET `/auth/me` | any | Current user, role, scope, allowed tools, features |
| GET `/auth/demo-users` | public | Demo users list for the login screen |
| GET `/auth/oidc/config` | public | OIDC settings (enabled, issuer, audience, jwks) |
| GET `/semantic` | any | Metrics (with certification status/version), dimension values, hierarchies, `as_of`, caller scope |
| GET `/data/freshness` | any | Source freshness vs cadence |
| GET `/data/quality?refresh=` | any | Data-quality check results (refresh re-runs checks) |
| GET `/tools` | any | Tools allowed for the caller with JSON schemas |
| POST `/tools/{name}` | any (role-checked per tool) | Run one governed tool directly with args; audited |

## Chat & conversations
| Method & path | Feature | Description |
|---|---|---|
| POST `/chat` | chat | `{message, conversation_id?}` → `{conversation, user_message, assistant_message}`; `assistant_message.payload` holds `evidence[]`, `suggestions[]`, `clarification`, `investigation`, `grounding`, `tools[]`, `mode`, `request_id` |
| GET `/suggestions` | any | Starter questions (top radar issues + defaults) |
| GET `/conversations?q=&archived=` | any | Own conversations; search matches titles and message text |
| GET `/conversations/{id}` | owner | Conversation + messages |
| PATCH `/conversations/{id}` | owner | `{title?, archived?}` |
| DELETE `/conversations/{id}` | owner | Deletes messages, evidence and investigations created from it (returns count) |
| GET `/conversations/{id}/export?format=md|json` | export | Download |
| GET `/evidence/{owner_type}/{owner_id}/{label}` | owner/visible | Full stored result: rows, chart, SQL + params, lineage, freshness, DQ, policy. `owner_type` = `conversation` or `investigation` |

## Business Pulse
| Method & path | Feature | Description |
|---|---|---|
| GET `/pulse/overview` | any | Health KPIs, movers, anomalies, sparkline |
| GET `/pulse/issues?refresh=` | any | Radar issues for the caller's scope (scans if none) |
| POST `/pulse/scan?auto_create=` | any (auto-create needs `investigate`) | Re-scan; optionally create investigations for issues ≥ threshold |
| POST `/pulse/issues/{id}/investigate` | investigate | Create/open the investigation for an issue |
| POST `/pulse/issues/{id}/dismiss` | any | Dismiss an issue |

## Investigations
| Method & path | Feature | Description |
|---|---|---|
| POST `/investigations` | investigate | `{observation, metric?, period?, compare_to?, filters?}` → full investigation |
| GET `/investigations?status=&q=` | any | List (only those visible under the caller's scope) |
| GET `/investigations/{id}` | visible | Detail incl. hypotheses, challenge, confidence, summary, evidence index, comments, actions, outcomes, shares, workflow tasks, similar issues |
| PATCH `/investigations/{id}` | investigate | `{status?, title?, priority?}`; `concluded`/`closed` stores to memory |
| DELETE `/investigations/{id}` | investigate (creator or admin) | Cascade delete |
| GET `/investigations/{id}/replay` | replay | Ordered steps |
| GET `/investigations/{id}/graph` | visible | Evidence graph nodes/edges |
| GET `/investigations/{id}/driver-tree` | visible | Driver tree, bridge chart, PVM |
| GET `/investigations/{id}/export?format=md|html|json` | export | Download |
| GET `/investigations/{id}/similar` | visible | Similar issues + hypothesis recall |
| POST `/investigations/{id}/assign` | assign | `{owner(username), due_date?, priority?}` + notification |
| POST `/investigations/{id}/comments` | comment | `{body}`; `@username` creates notifications |
| POST `/investigations/{id}/share` | share | `{mode:"link"|"users", users[], expires_hours}`; link mode returns `{token,path}` |
| DELETE `/investigations/{id}/share/{token}` | share | Revoke |
| GET `/shared/{token}` | public | Read-only sanitised snapshot (expiry/revocation enforced) |
| POST `/investigations/{id}/actions` | investigate | `{title, description?, owner?, due_date?}` |
| PATCH `/actions/{id}` | investigate | `{status: open|in_progress|done}` |
| GET `/actions?mine=` | any | Action tracker across investigations |
| POST `/investigations/{id}/outcomes` | investigate | Record action/result/metrics (updates memory) |
| GET `/investigations/{id}/outcome-monitor` | visible | Baseline vs issue vs post-action level; recovery % |
| POST `/investigations/{id}/workflow` | investigate | Create workflow task; POSTs to `WORKFLOW_WEBHOOK_URL` if set |

## Memory & notifications
| Method & path | Description |
|---|---|
| GET `/memory/issues?q=` | Search institutional memory |
| GET `/memory/issues/{id}` | One memory record |
| GET `/notifications` / POST `/notifications/read` | Own notifications / mark read |

## Governance
| Method & path | Feature | Description |
|---|---|---|
| GET `/governance/metrics` | any | Catalog with version history |
| PUT `/governance/metrics/{key}` | metric_admin | `{description, status: certified|draft|deprecated, owner?}`; description change bumps version; deprecated blocks use |
| GET `/governance/audit?user=&action=&limit=` | audit_view | Audit trail (max 500) |
| GET `/governance/rbac` | any | Roles, caller; user list only with `user_admin` |
| GET `/governance/lineage` | any | Metric → table → system lineage and sources |

## Operations & integrations
| Method & path | Feature | Description |
|---|---|---|
| GET `/admin/telemetry` | telemetry_view | LLM and tool call counts, failures, p50/p95, tokens |
| GET `/integrations` | any | Connector status |
| POST `/integrations/test-connection` | integrations | Row count + dialect of the analytics DB |
| GET `/integrations/bi-links?investigation_id=` | any | BI deep links with filters from the investigation |

## Example
```bash
TOKEN=$(curl -s localhost:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"username":"analyst","password":"demo123"}' | jq -r .token)

curl -s localhost:8000/api/tools/compare_periods -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"metric":"revenue","period":"last_4_weeks","group_by":["region"]}'
```
Tool argument conventions: `period` ∈ `last_N_weeks`, `last_week`, `last_month`, `last_quarter`, `this_month`, `this_quarter`, `ytd`, `last_year`, `YYYY-MM`, `YYYY-Qn`, `YYYY`, `YYYY-MM-DD..YYYY-MM-DD`; `compare_to` ∈ `prior_period`, `prior_year`, `none`; `filters` is `{dimension: [exact values]}`.
