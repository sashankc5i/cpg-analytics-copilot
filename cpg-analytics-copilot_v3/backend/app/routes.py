import hashlib
import html as htmllib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from . import agent, governance, investigation as inv_mod, memory, security, telemetry, tools
from . import semantic as S
from .analytics import core as C
from .analytics import ops
from .config import settings
from .db import engine, fetch_df, jd, jl, now, q, q1, uid, x
from .governance import audit
from .llm import llm
from .logging_setup import log, request_id_var
from .security import current_user, require

api = APIRouter(prefix="/api")


# ------------------------------------------------------------- helpers
def _scope_hash(u):
    return "global" if not u["scope"] else hashlib.md5(json.dumps(u["scope"], sort_keys=True).encode()).hexdigest()[:8]


def can_view(u, inv):
    if not u["scope"]:
        return True
    sc = inv.get("scope") or {}
    return all(d in sc and set(sc[d]) <= set(v) for d, v in u["scope"].items())


def get_inv(u, inv_id):
    inv = inv_mod.get(inv_id)
    if not inv or not can_view(u, inv):
        raise HTTPException(404, "Investigation not found.")
    return inv


def notify(username, kind, body, link):
    r = q1("SELECT id FROM users WHERE username=?", (username,))
    if r:
        x("INSERT INTO notifications VALUES(?,?,?,?,?,?,?)", (uid("n_"), r["id"], kind, body, link, 0, now()))


# ------------------------------------------------------------- auth / meta
class Login(BaseModel):
    username: str
    password: str


@api.get("/health")
def health():
    return {"status": "ok", "llm": "groq" if llm.available else "offline", "model": settings.groq_model if llm.available else None, "request_id": request_id_var.get()}


@api.post("/auth/login")
def login(b: Login):
    r = security.login(b.username, b.password); audit(r["user"], "auth.login"); return r


@api.get("/auth/me")
def me(u=Depends(current_user)):
    return u


@api.get("/auth/demo-users")
def demo_users():
    return {"mode": settings.auth_mode, "password_hint": settings.demo_password if settings.auth_mode == "local" else None,
            "users": [{"username": a, "name": b, "role": c, "scope": d} for a, b, c, d in security.DEMO]}


@api.get("/auth/oidc/config")
def oidc_cfg():
    return {"enabled": settings.auth_mode == "oidc", "issuer": settings.oidc_issuer, "audience": settings.oidc_audience, "jwks_url": settings.oidc_jwks_url}


@api.get("/semantic")
def semantic(u=Depends(current_user)):
    defs = {r["key"]: r for r in q("SELECT * FROM metric_defs")}
    return {"metrics": [{"key": k, "name": m["name"], "unit": m["unit"], "additive": m["additive"], "source": m["source"], "status": defs.get(k, {}).get("status"), "version": defs.get(k, {}).get("version")} for k, m in S.METRICS.items()],
            "dimensions": C.dim_values(), "hierarchies": S.HIERARCHIES, "as_of": C.as_of().isoformat(), "scope": u["scope"]}


@api.get("/data/freshness")
def freshness(u=Depends(current_user)):
    ctx = C.Ctx(); ctx.tables.update(["fact_sales", "fact_inventory", "fact_promotions", "fact_competitor", "fact_cohorts"])
    return {"sources": ops.freshness_info(ctx), "data_through": (C.as_of() + timedelta(days=6)).isoformat()}


@api.get("/data/quality")
def quality(refresh: bool = False, u=Depends(current_user)):
    if refresh:
        ops.run_dq_checks()
    df = fetch_df("SELECT * FROM dq_results").astype(object)
    return {"checks": df.where(df.notna(), None).to_dict("records")}


@api.post("/tools/{name}")
def run_tool(name: str, args: dict = Body(default={}), u=Depends(current_user)):
    res = tools.execute(name, args, u, request_id_var.get())
    audit(u, "tool.run", {"tool": name, "args": args, "ok": "error" not in res})
    if "error" in res:
        raise HTTPException(403 if res["kind"] == "policy" else 400, res["error"])
    return res


@api.get("/tools")
def list_tools(u=Depends(current_user)):
    return [{"name": t.name, "description": t.desc, "tier": t.tier, "parameters": t.schema} for t in tools.allowed(u["role"])]


# ------------------------------------------------------------- conversations
class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None


@api.post("/chat")
def chat(b: ChatIn, u=Depends(require("chat"))):
    if not b.message.strip():
        raise HTTPException(400, "Message is empty.")
    try:
        return agent.chat(u, b.message.strip()[:2000], b.conversation_id, request_id_var.get())
    except LookupError as e:
        raise HTTPException(404, str(e))


@api.get("/suggestions")
def suggestions(u=Depends(current_user)):
    return {"suggestions": agent.starter_suggestions()}


@api.get("/conversations")
def conversations(q_: str = Query("", alias="q"), archived: bool = False, u=Depends(current_user)):
    rows = q("SELECT id,title,archived,created_at,updated_at FROM conversations WHERE user_id=? AND archived=? ORDER BY updated_at DESC", (u["id"], int(archived)))
    if q_:
        ids = {r["conversation_id"] for r in q("SELECT DISTINCT conversation_id FROM messages WHERE content LIKE ?", (f"%{q_}%",))}
        rows = [r for r in rows if q_.lower() in r["title"].lower() or r["id"] in ids]
    return rows


def _conv(u, cid):
    c = q1("SELECT * FROM conversations WHERE id=? AND user_id=?", (cid, u["id"]))
    if not c:
        raise HTTPException(404, "Conversation not found.")
    return c


@api.get("/conversations/{cid}")
def conversation(cid: str, u=Depends(current_user)):
    c = _conv(u, cid)
    msgs = [{**m, "payload": jl(m.pop("payload_json"))} for m in q("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at", (cid,))]
    return {"conversation": {k: c[k] for k in ("id", "title", "archived", "created_at", "updated_at")}, "messages": msgs}


class ConvPatch(BaseModel):
    title: str | None = None
    archived: bool | None = None


@api.patch("/conversations/{cid}")
def patch_conv(cid: str, b: ConvPatch, u=Depends(current_user)):
    _conv(u, cid)
    if b.title is not None:
        x("UPDATE conversations SET title=? WHERE id=?", (b.title.strip()[:100] or "Untitled", cid))
    if b.archived is not None:
        x("UPDATE conversations SET archived=? WHERE id=?", (int(b.archived), cid))
    audit(u, "conversation.update", {"id": cid, **b.model_dump(exclude_none=True)})
    return {"ok": True}


def _delete_investigation(iid):
    for t in ("comments", "shares", "actions", "outcomes"):
        x(f"DELETE FROM {t} WHERE investigation_id=?", (iid,))
    x("DELETE FROM evidence WHERE owner_type='investigation' AND owner_id=?", (iid,))
    x("DELETE FROM issue_memory WHERE investigation_id=?", (iid,))
    x("DELETE FROM workflow_tasks WHERE investigation_id=?", (iid,))
    x("UPDATE radar_issues SET investigation_id=NULL, status='new' WHERE investigation_id=?", (iid,))
    x("DELETE FROM investigations WHERE id=?", (iid,))


@api.delete("/conversations/{cid}")
def delete_conv(cid: str, u=Depends(current_user)):
    _conv(u, cid)
    invs = [r["id"] for r in q("SELECT id FROM investigations WHERE conversation_id=?", (cid,))]
    for i in invs:
        _delete_investigation(i)
    x("DELETE FROM evidence WHERE owner_type='conversation' AND owner_id=?", (cid,))
    x("DELETE FROM messages WHERE conversation_id=?", (cid,)); x("DELETE FROM conversations WHERE id=?", (cid,))
    audit(u, "conversation.delete", {"id": cid, "investigations_deleted": invs})
    return {"ok": True, "investigations_deleted": len(invs)}


@api.get("/evidence/{owner_type}/{owner_id}/{label}")
def evidence(owner_type: str, owner_id: str, label: str, u=Depends(current_user)):
    if owner_type == "conversation":
        _conv(u, owner_id)
    elif owner_type == "investigation":
        get_inv(u, owner_id)
    else:
        raise HTTPException(400, "Unknown owner type.")
    r = q1("SELECT * FROM evidence WHERE owner_type=? AND owner_id=? AND label=?", (owner_type, owner_id, label))
    if not r:
        raise HTTPException(404, "Evidence not found.")
    return {"label": r["label"], "tool": r["tool"], "args": jl(r["args_json"]), "created_at": r["created_at"], "result": jl(r["result_json"])}


def _conv_md(c, msgs):
    out = [f"# {c['title']}", f"_Exported {now()}_", ""]
    for m in msgs:
        out += [f"**{'You' if m['role'] == 'user' else 'Copilot'}**", "", m["content"], ""]
        for e in (jl(m["payload_json"], {}) or {}).get("evidence", []) if m.get("payload_json") else []:
            out.append(f"> [{e['label']}] {e['tool']}: {e['headline']}")
        out.append("")
    return "\n".join(out)


@api.get("/conversations/{cid}/export")
def export_conv(cid: str, format: str = "md", u=Depends(require("export"))):
    c = _conv(u, cid); msgs = q("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at", (cid,))
    audit(u, "conversation.export", {"id": cid, "format": format})
    if format == "json":
        return {"conversation": c, "messages": msgs}
    return PlainTextResponse(_conv_md(c, msgs), media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="conversation-{cid}.md"'})


# ------------------------------------------------------------- pulse / radar
def _scan(u, auto_create=False):
    sid = _scope_hash(u)
    res = tools.execute("detect_business_issues", {"limit": 15}, u, request_id_var.get())
    if "error" in res:
        raise HTTPException(400, res["error"])
    created = []
    for it in res["facts"]["issues"]:
        key = f"{it['id']}:{sid}"; ex = q1("SELECT * FROM radar_issues WHERE id=?", (key,))
        status = ex["status"] if ex else "new"; inv_id = ex["investigation_id"] if ex else None
        if auto_create and status == "new" and it["score"] >= settings.auto_investigate_threshold and "investigate" in u["features"]:
            try:
                inv = inv_mod.start(u, it["title"], it["spec"], None, "radar", it["id"], request_id_var.get(), "high")
                status, inv_id = "investigating", inv["id"]; created.append(inv["id"])
                for mgr in q("SELECT username FROM users WHERE role IN ('manager','admin')"):
                    notify(mgr["username"], "radar", f"New proactive investigation: {it['title']}", f"/investigations/{inv['id']}")
            except Exception as e:
                log("radar", logging.ERROR, "auto investigation failed", error=repr(e)[:200])
        x("DELETE FROM radar_issues WHERE id=?", (key,))
        x("INSERT INTO radar_issues VALUES(?,?,?,?,?,?,?)", (key, jd(it), it["score"], status, inv_id, sid, now()))
    audit(u, "radar.scan", {"issues": len(res["facts"]["issues"]), "auto_created": created})
    return created


def _issues(u):
    sid = _scope_hash(u)
    return [{**jl(r["data_json"]), "status": r["status"], "investigation_id": r["investigation_id"], "detected_at": r["detected_at"]} for r in q("SELECT * FROM radar_issues WHERE id LIKE ? ORDER BY score DESC", (f"%:{sid}",))]


@api.get("/pulse/overview")
def pulse_overview(u=Depends(current_user)):
    res = tools.execute("business_health_overview", {}, u, request_id_var.get())
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@api.get("/pulse/issues")
def pulse_issues(refresh: bool = False, u=Depends(current_user)):
    if refresh or not _issues(u):
        _scan(u)
    return {"issues": _issues(u)}


@api.post("/pulse/scan")
def pulse_scan(auto_create: bool = True, u=Depends(current_user)):
    created = _scan(u, auto_create); return {"created_investigations": created, "issues": _issues(u)}


@api.post("/pulse/issues/{iid}/investigate")
def investigate_issue(iid: str, u=Depends(require("investigate"))):
    r = q1("SELECT * FROM radar_issues WHERE id=?", (f"{iid}:{_scope_hash(u)}",))
    if not r:
        raise HTTPException(404, "Issue not found.")
    if r["investigation_id"] and inv_mod.get(r["investigation_id"]):
        return {"id": r["investigation_id"]}
    it = jl(r["data_json"]); inv = inv_mod.start(u, it["title"], it["spec"], None, "radar", iid, request_id_var.get(), "high" if it["severity"] == "high" else "medium")
    x("UPDATE radar_issues SET status='investigating', investigation_id=? WHERE id=?", (inv["id"], r["id"]))
    return {"id": inv["id"]}


@api.post("/pulse/issues/{iid}/dismiss")
def dismiss_issue(iid: str, u=Depends(current_user)):
    x("UPDATE radar_issues SET status='dismissed' WHERE id=?", (f"{iid}:{_scope_hash(u)}",)); audit(u, "radar.dismiss", {"id": iid}); return {"ok": True}


# ------------------------------------------------------------- investigations
class InvIn(BaseModel):
    observation: str
    metric: str | None = None
    period: str | None = None
    compare_to: str | None = None
    filters: dict | None = None


@api.post("/investigations")
def create_inv(b: InvIn, u=Depends(require("investigate"))):
    try:
        return inv_mod.start(u, b.observation, {"metric": b.metric, "period": b.period, "compare_to": b.compare_to, "filters": b.filters}, None, request_id=request_id_var.get())
    except ValueError as e:
        raise HTTPException(400, str(e))


@api.get("/investigations")
def list_inv(status: str | None = None, q_: str = Query("", alias="q"), u=Depends(current_user)):
    out = []
    for r in q("SELECT id FROM investigations ORDER BY updated_at DESC"):
        i = inv_mod.get(r["id"])
        if not can_view(u, i) or (status and i["status"] != status) or (q_ and q_.lower() not in (i["title"] + i["observation"]).lower()):
            continue
        out.append({k: i.get(k) for k in ("id", "title", "status", "priority", "owner", "due_date", "source", "created_at", "updated_at")} | {"confidence": i["confidence"]["level"], "gap_pct": i["gap"]["pct"],
                    "lead": next((h["statement"] for h in i["hypotheses"] if h["status"] == "supported" and h["category"] == "Cause"), None)})
    return out


@api.get("/investigations/{iid}")
def get_one(iid: str, u=Depends(current_user)):
    i = get_inv(u, iid); i.pop("graph", None); i.pop("replay", None)
    i["comments"] = comments(iid, u); i["actions"] = q("SELECT * FROM actions WHERE investigation_id=?", (iid,)); i["outcomes"] = q("SELECT * FROM outcomes WHERE investigation_id=?", (iid,))
    i["shares"] = q("SELECT token,permission,expires_at,created_at,revoked FROM shares WHERE investigation_id=?", (iid,)); i["workflow_tasks"] = q("SELECT id,title,system,external_ref,status,created_at FROM workflow_tasks WHERE investigation_id=?", (iid,))
    return i


@api.get("/investigations/{iid}/replay")
def replay(iid: str, u=Depends(require("replay"))):
    i = get_inv(u, iid); audit(u, "investigation.replay", {"id": iid}); return {"id": iid, "title": i["title"], "steps": i["replay"]}


@api.get("/investigations/{iid}/graph")
def graph(iid: str, u=Depends(current_user)):
    return get_inv(u, iid)["graph"]


@api.get("/investigations/{iid}/driver-tree")
def driver_tree(iid: str, u=Depends(current_user)):
    get_inv(u, iid)
    r = q1("SELECT result_json, label FROM evidence WHERE owner_type='investigation' AND owner_id=? AND tool='driver_decomposition' ORDER BY created_at LIMIT 1", (iid,))
    if not r:
        raise HTTPException(404, "No driver decomposition for this investigation.")
    res = jl(r["result_json"]); return {"label": r["label"], "tree": res["facts"]["tree"], "levels": res["facts"]["tree_levels"], "gap": res["facts"]["gap"], "pvm": res["facts"].get("pvm"), "chart": res["chart"], "metric": res["facts"]["metric"]}


class InvPatch(BaseModel):
    status: str | None = None
    title: str | None = None
    priority: str | None = None


@api.patch("/investigations/{iid}")
def patch_inv(iid: str, b: InvPatch, u=Depends(require("investigate"))):
    i = get_inv(u, iid)
    if b.title: i["title"] = b.title[:200]
    if b.priority in ("low", "medium", "high"): i["priority"] = b.priority
    if b.status:
        if b.status not in ("open", "in_progress", "concluded", "closed"):
            raise HTTPException(400, "Invalid status.")
        i["status"] = b.status
        if b.status in ("concluded", "closed") and not i.get("concluded_at"):
            i["concluded_at"] = now(); memory.store(i, u)
    inv_mod.save(i); audit(u, "investigation.update", {"id": iid, **b.model_dump(exclude_none=True)}); return {"ok": True}


@api.delete("/investigations/{iid}")
def delete_inv(iid: str, u=Depends(require("investigate"))):
    i = get_inv(u, iid)
    if i["user_id"] != u["id"] and u["role"] != "admin":
        raise HTTPException(403, "Only the creator or an admin can delete an investigation.")
    _delete_investigation(iid); audit(u, "investigation.delete", {"id": iid}); return {"ok": True}


def _inv_md(i):
    s = i["summary"]; L = [f"# {i['title']}", f"*Status: {i['status']} · Priority: {i['priority']} · Confidence: {i['confidence']['level']} ({i['confidence']['score']}/100) · Exported {now()}*", "", "## Observation", i["observation"], "", "## Summary", s["narrative"], "", "**Conclusion:** " + s["conclusion"], "", "## Hypothesis ledger"]
    L += [f"- **{h['key']}** — {h['status']} ({h['explained_pct']}% of gap, score {h.get('score')}): {h['rationale']} {' '.join('[' + e + ']' for e in h['evidence'])}" for h in i["hypotheses"] if h["status"] != "untestable"]
    L += ["", "## Challenge", "**Contradictions**"] + [f"- {c['text']}" for c in i["challenge"]["contradictions"]] + ["**Alternatives**"] + [f"- {a['statement']} ({a['status']}, {a['explained_pct']}%)" for a in i["challenge"]["alternatives"]]
    L += ["**Missing evidence**"] + [f"- {m['text']} (needed: {m['data_needed']})" for m in i["challenge"]["missing_evidence"]]
    L += ["", "## Claims → evidence"] + [f"- ({c['kind']}) {c['text']} {' '.join('[' + e + ']' for e in c['evidence'])}" for c in s["claims"]]
    L += ["", "## Recommendations (separate from evidence)"] + [f"- **{r['action']}**  \n  Rationale: {r['rationale']}  \n  Assumptions: {'; '.join(r['assumptions'])}  \n  Expected impact: {r['expected_impact']}" for r in s["recommendations"]]
    L += ["", "## Evidence index"] + [f"- [{e['label']}] {e['tool']}: {e['headline']}" for e in i["evidence"]]
    return "\n".join(L)


@api.get("/investigations/{iid}/export")
def export_inv(iid: str, format: str = "md", u=Depends(require("export"))):
    i = get_inv(u, iid); audit(u, "investigation.export", {"id": iid, "format": format})
    if format == "json":
        return i
    md = _inv_md(i)
    if format == "html":
        body = htmllib.escape(md).replace("\n", "<br>")
        return Response(f"<html><head><meta charset='utf-8'><title>{htmllib.escape(i['title'])}</title><style>body{{font-family:system-ui;max-width:820px;margin:2rem auto;line-height:1.5}}</style></head><body>{body}</body></html>", media_type="text/html")
    return PlainTextResponse(md, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="investigation-{iid}.md"'})


@api.get("/investigations/{iid}/similar")
def similar(iid: str, u=Depends(current_user)):
    i = get_inv(u, iid); s = memory.find_similar(i); return {"similar": s, "recall": memory.hypothesis_recall(s)}


# --- collaboration
class Assign(BaseModel):
    owner: str
    due_date: str | None = None
    priority: str | None = None


@api.post("/investigations/{iid}/assign")
def assign(iid: str, b: Assign, u=Depends(require("assign"))):
    i = get_inv(u, iid)
    if not q1("SELECT id FROM users WHERE username=?", (b.owner,)):
        raise HTTPException(400, "Unknown owner username.")
    i["owner"], i["due_date"] = b.owner, b.due_date
    if b.priority in ("low", "medium", "high"): i["priority"] = b.priority
    inv_mod.save(i); notify(b.owner, "assignment", f"You were assigned: {i['title']}" + (f" (due {b.due_date})" if b.due_date else ""), f"/investigations/{iid}")
    audit(u, "investigation.assign", {"id": iid, "owner": b.owner, "due": b.due_date}); return {"ok": True}


class Comment(BaseModel):
    body: str


def comments(iid, u):
    return [{**r, "mentions": jl(r.pop("mentions_json"), [])} for r in q("SELECT c.*, u.display_name author FROM comments c LEFT JOIN users u ON u.id=c.user_id WHERE investigation_id=? ORDER BY created_at", (iid,))]


@api.post("/investigations/{iid}/comments")
def add_comment(iid: str, b: Comment, u=Depends(require("comment"))):
    get_inv(u, iid)
    names = [n for n in re.findall(r"@(\w+)", b.body) if q1("SELECT id FROM users WHERE username=?", (n,))]
    x("INSERT INTO comments VALUES(?,?,?,?,?,?)", (uid("cm_"), iid, u["id"], b.body[:2000], jd(names), now()))
    for n in set(names):
        notify(n, "mention", f"{u['display_name']} mentioned you: {b.body[:80]}", f"/investigations/{iid}")
    audit(u, "comment.add", {"id": iid, "mentions": names}); return comments(iid, u)


class ShareIn(BaseModel):
    mode: str = "link"
    users: list[str] = []
    expires_hours: int = 72


@api.post("/investigations/{iid}/share")
def share(iid: str, b: ShareIn, u=Depends(require("share"))):
    i = get_inv(u, iid); out = {}
    if b.mode == "link":
        tok = uid("sh_") + uid(); x("INSERT INTO shares VALUES(?,?,?,?,?,?,?)", (tok, iid, u["id"], "view", (datetime.now(timezone.utc) + timedelta(hours=min(b.expires_hours, 720))).isoformat(timespec="seconds"), now(), 0)); out["token"] = tok; out["path"] = f"/shared/{tok}"
    for n in b.users:
        notify(n, "share", f"{u['display_name']} shared an investigation: {i['title']}", f"/investigations/{iid}")
    audit(u, "investigation.share", {"id": iid, "mode": b.mode, "users": b.users}); return out


@api.delete("/investigations/{iid}/share/{token}")
def revoke(iid: str, token: str, u=Depends(require("share"))):
    get_inv(u, iid); x("UPDATE shares SET revoked=1 WHERE token=? AND investigation_id=?", (token, iid)); audit(u, "investigation.unshare", {"id": iid}); return {"ok": True}


@api.get("/shared/{token}")
def shared(token: str):
    s = q1("SELECT * FROM shares WHERE token=?", (token,))
    if not s or s["revoked"] or s["expires_at"] < datetime.now(timezone.utc).isoformat(timespec="seconds"):
        raise HTTPException(404, "This shared link is invalid, revoked or expired.")
    i = inv_mod.get(s["investigation_id"])
    charts = []
    for r in q("SELECT label, tool, result_json FROM evidence WHERE owner_type='investigation' AND owner_id=? ORDER BY created_at", (i["id"],)):
        res = jl(r["result_json"])
        if res.get("chart"): charts.append({"label": r["label"], "tool": r["tool"], "headline": res["headline"], "chart": res["chart"]})
    audit({"id": "public", "role": "public"}, "shared.view", {"token": token[:8], "investigation": i["id"]})
    return {"title": i["title"], "status": i["status"], "confidence": i["confidence"], "summary": i["summary"], "challenge": i["challenge"], "gap": i["gap"],
            "hypotheses": [{k: h[k] for k in ("key", "statement", "status", "explained_pct", "rationale", "evidence")} for h in i["hypotheses"] if h["status"] != "untestable"], "evidence": i["evidence"], "charts": charts[:6], "read_only": True}


# --- actions, outcomes, workflow
class ActionIn(BaseModel):
    title: str
    description: str = ""
    owner: str | None = None
    due_date: str | None = None


@api.post("/investigations/{iid}/actions")
def add_action(iid: str, b: ActionIn, u=Depends(require("investigate"))):
    get_inv(u, iid); aid = uid("act_")
    x("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?,?)", (aid, iid, b.title, b.description, b.owner, b.due_date, "open", u["username"], now(), None))
    if b.owner: notify(b.owner, "action", f"Action assigned: {b.title}", f"/investigations/{iid}")
    audit(u, "action.create", {"id": aid, "investigation": iid}); return {"id": aid}


class ActionPatch(BaseModel):
    status: str


@api.patch("/actions/{aid}")
def patch_action(aid: str, b: ActionPatch, u=Depends(require("investigate"))):
    if b.status not in ("open", "in_progress", "done"):
        raise HTTPException(400, "Invalid status.")
    x("UPDATE actions SET status=?, completed_at=? WHERE id=?", (b.status, now() if b.status == "done" else None, aid)); audit(u, "action.update", {"id": aid, "status": b.status}); return {"ok": True}


@api.get("/actions")
def all_actions(mine: bool = False, u=Depends(current_user)):
    rows = q("SELECT a.*, i.title investigation_title FROM actions a LEFT JOIN investigations i ON i.id=a.investigation_id ORDER BY a.created_at DESC")
    return [r for r in rows if not mine or r["owner"] == u["username"]]


class OutcomeIn(BaseModel):
    action: str
    result: str
    metric_before: float | None = None
    metric_after: float | None = None
    notes: str = ""


@api.post("/investigations/{iid}/outcomes")
def add_outcome(iid: str, b: OutcomeIn, u=Depends(require("investigate"))):
    get_inv(u, iid); oid = memory.record_outcome(iid, u, b.action, b.result, b.metric_before, b.metric_after, b.notes); audit(u, "outcome.record", {"id": oid, "investigation": iid}); return {"id": oid}


@api.get("/investigations/{iid}/outcome-monitor")
def outcome_monitor(iid: str, u=Depends(current_user)):
    return memory.monitor_outcome(get_inv(u, iid), u)


@api.post("/investigations/{iid}/workflow")
def workflow(iid: str, u=Depends(require("investigate"))):
    i = get_inv(u, iid); tid = uid("wf_"); payload = {"title": f"[CPG Copilot] {i['title']}", "priority": i["priority"], "summary": i["summary"]["conclusion"], "owner": i["owner"], "due_date": i["due_date"], "link": f"/investigations/{iid}"}
    system, ref, status = "internal", tid, "created"
    if settings.workflow_webhook:
        try:
            r = httpx.post(settings.workflow_webhook, json=payload, timeout=6); system, status = "webhook", "sent" if r.status_code < 300 else f"failed ({r.status_code})"
            ref = r.headers.get("x-task-id", tid)
        except Exception as e:
            status = "failed (unreachable)"; log("workflow", logging.WARNING, "webhook failed", error=str(e)[:120])
    x("INSERT INTO workflow_tasks VALUES(?,?,?,?,?,?,?,?)", (tid, iid, payload["title"], system, ref, status, jd(payload), now())); audit(u, "workflow.task", {"id": tid, "system": system, "status": status})
    return {"id": tid, "system": system, "status": status, "payload": payload}


# ------------------------------------------------------------- memory
@api.get("/memory/issues")
def memory_issues(q_: str = Query("", alias="q"), u=Depends(current_user)):
    return memory.search(q_)


@api.get("/memory/issues/{mid}")
def memory_issue(mid: str, u=Depends(current_user)):
    r = q1("SELECT * FROM issue_memory WHERE id=?", (mid,))
    if not r: raise HTTPException(404, "Not found.")
    return {**r, "signature": jl(r["signature_json"]), "hypotheses": jl(r["hypotheses_json"]), "outcome": jl(r["outcome_json"])}


# ------------------------------------------------------------- notifications
@api.get("/notifications")
def notifications(u=Depends(current_user)):
    return q("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (u["id"],))


@api.post("/notifications/read")
def read_notifications(u=Depends(current_user)):
    x("UPDATE notifications SET read=1 WHERE user_id=?", (u["id"],)); return {"ok": True}


# ------------------------------------------------------------- governance
@api.get("/governance/metrics")
def gov_metrics(u=Depends(current_user)):
    hist = q("SELECT * FROM metric_history ORDER BY ts DESC")
    return [{**m, "formula": S.METRICS[m["key"]]["formula"], "history": [h for h in hist if h["key"] == m["key"]][:5]} for m in q("SELECT * FROM metric_defs")]


class MetricIn(BaseModel):
    description: str
    status: str = "certified"
    owner: str | None = None


@api.put("/governance/metrics/{key}")
def gov_metric_update(key: str, b: MetricIn, u=Depends(require("metric_admin"))):
    if b.status not in ("certified", "draft", "deprecated"):
        raise HTTPException(400, "status must be certified, draft or deprecated.")
    r = governance.update_metric(u, key, b.description, b.status, b.owner)
    if not r: raise HTTPException(404, "Unknown metric.")
    return r


@api.get("/governance/audit")
def gov_audit(user: str | None = None, action: str | None = None, limit: int = 100, u=Depends(require("audit_view"))):
    sql, p = "SELECT * FROM audit WHERE 1=1", []
    if user: sql += " AND user_id LIKE ?"; p.append(f"%{user}%")
    if action: sql += " AND action LIKE ?"; p.append(f"%{action}%")
    return [{**r, "detail": jl(r.pop("detail_json"))} for r in q(sql + " ORDER BY ts DESC LIMIT ?", (*p, min(limit, 500)))]


@api.get("/governance/rbac")
def gov_rbac(u=Depends(current_user)):
    return {"me": u, "roles": {r: {"tools": v["tools"], "features": sorted(v["features"])} for r, v in security.ROLES.items()},
            "users": [{"username": r["username"], "display_name": r["display_name"], "role": r["role"], "scope": jl(r["scope_json"], {})} for r in q("SELECT * FROM users")] if "user_admin" in u["features"] else []}


@api.get("/governance/lineage")
def gov_lineage(u=Depends(current_user)):
    ctx = C.Ctx(); ctx.tables.update(["fact_sales", "fact_inventory", "fact_promotions", "fact_competitor", "fact_cohorts"]); fr = {f["table"]: f for f in ops.freshness_info(ctx)}
    tbl = {"sales": "fact_sales", "inventory": "fact_inventory"}
    return {"metrics": [{"key": k, "name": m["name"], "formula": m["formula"], "source_table": tbl[m["source"]], "system": fr[tbl[m["source"]]]["system"], "last_refreshed": fr[tbl[m["source"]]]["last_refreshed"], "transformations": tools.LINEAGE_STEPS} for k, m in S.METRICS.items()],
            "sources": list(fr.values())}


# ------------------------------------------------------------- observability / integrations
@api.get("/admin/telemetry")
def telem(u=Depends(require("telemetry_view"))):
    return telemetry.summary()


@api.get("/integrations")
def integrations(u=Depends(current_user)):
    az = settings.analytics_url.startswith("mssql")
    return {"connectors": [
        {"id": "sqlite", "name": "Synthetic CPG warehouse (SQLite)", "kind": "database", "status": "disabled" if az else "active", "detail": "Bundled demo data"},
        {"id": "azure_sql", "name": "Azure SQL (governed)", "kind": "database", "status": "active" if az else "not configured", "detail": "Set ANALYTICS_DB_URL=mssql+pyodbc://… and provide the fact_* tables/views."},
        {"id": "groq", "name": "Groq LLM", "kind": "llm", "status": "active" if llm.available else "offline planner", "detail": settings.groq_model if llm.available else "Set GROQ_API_KEY"},
        {"id": "oidc", "name": "Enterprise identity (OIDC)", "kind": "identity", "status": "active" if settings.auth_mode == "oidc" else "local demo auth", "detail": "AUTH_MODE=oidc + OIDC_JWKS_URL"},
        {"id": "workflow", "name": "Workflow tasks (webhook)", "kind": "workflow", "status": "active" if settings.workflow_webhook else "internal only", "detail": "WORKFLOW_WEBHOOK_URL (Jira/ServiceNow/Teams-compatible JSON)"},
        {"id": "bi", "name": "BI dashboards (Power BI)", "kind": "bi", "status": "configured" if "REPORT_ID" not in settings.bi_url else "template", "detail": settings.bi_url}]}


@api.post("/integrations/test-connection")
def test_conn(u=Depends(require("integrations"))):
    try:
        n = int(fetch_df("SELECT COUNT(*) AS n FROM fact_sales").n.iloc[0]); return {"ok": True, "rows_in_fact_sales": n, "dialect": engine().dialect.name}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@api.get("/integrations/bi-links")
def bi_links(investigation_id: str | None = None, u=Depends(current_user)):
    flt = {}
    if investigation_id:
        flt = get_inv(u, investigation_id)["spec"]["filters"]
    qs = " and ".join(f"Sales/{k} eq '{v[0]}'" for k, v in flt.items() if v)
    sfx = (f"&filter={quote(qs)}" if qs else "")
    return [{"name": n, "url": f"{settings.bi_url}?pageName={p}{sfx}"} for n, p in [("Revenue overview", "ReportSectionRevenue"), ("Inventory & availability", "ReportSectionInventory"), ("Promotions", "ReportSectionPromo")]]
