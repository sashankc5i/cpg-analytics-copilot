import os, sys, tempfile
d = tempfile.mkdtemp()
os.environ.update(STATE_DB=f"{d}/state.db", ANALYTICS_DB_URL=f"sqlite:///{d}/cpg.db", GROQ_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as c:
        yield c


def H(c, user="admin"):
    t = c.post("/api/auth/login", json={"username": user, "password": "demo123"}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def test_auth_and_request_id(c):
    assert c.post("/api/auth/login", json={"username": "admin", "password": "bad"}).status_code == 401
    r = c.get("/api/auth/me"); assert r.status_code == 401 and "request_id" in r.json() and r.headers["X-Request-ID"]
    assert c.get("/api/auth/me", headers=H(c)).json()["role"] == "admin"


def test_chat_flow_and_conversation_lifecycle(c):
    h = H(c)
    r = c.post("/api/chat", json={"message": "Which regions declined the most last month?"}, headers=h).json()
    a = r["assistant_message"]; cid = r["conversation"]["id"]
    assert a["payload"]["evidence"] and "[E1]" in a["content"] and a["payload"]["suggestions"]
    ev = c.get(f"/api/evidence/conversation/{cid}/E1", headers=h).json()
    assert ev["result"]["meta"]["sql"] and ev["result"]["meta"]["freshness"]["sources"]
    r2 = c.post("/api/chat", json={"message": "and for Beverages?", "conversation_id": cid}, headers=h).json()
    assert r2["assistant_message"]["payload"]["evidence"]
    assert c.patch(f"/api/conversations/{cid}", json={"title": "Renamed", "archived": True}, headers=h).status_code == 200
    assert any(x["id"] == cid for x in c.get("/api/conversations?archived=true", headers=h).json())
    assert c.get(f"/api/conversations/{cid}/export", headers=h).status_code == 200
    amb = c.post("/api/chat", json={"message": "hmm"}, headers=h).json()["assistant_message"]["payload"]
    assert amb["clarification"]["options"]


def test_investigation_end_to_end(c):
    h = H(c)
    r = c.post("/api/chat", json={"message": "Why did revenue drop in the last 4 weeks?"}, headers=h).json()
    inv_id = r["assistant_message"]["payload"]["investigation"]["id"]; cid = r["conversation"]["id"]
    i = c.get(f"/api/investigations/{inv_id}", headers=h).json()
    keys = {x["key"]: x for x in i["hypotheses"]}
    assert keys["STOCKOUT"]["status"] == "supported" and i["challenge"]["missing_evidence"] and i["confidence"]["factors"]
    assert c.get(f"/api/investigations/{inv_id}/replay", headers=h).json()["steps"]
    assert c.get(f"/api/investigations/{inv_id}/graph", headers=h).json()["edges"]
    assert c.get(f"/api/investigations/{inv_id}/driver-tree", headers=h).json()["tree"]["children"]
    assert c.get(f"/api/investigations/{inv_id}/export?format=md", headers=h).status_code == 200
    # collaboration
    assert c.post(f"/api/investigations/{inv_id}/assign", json={"owner": "analyst", "due_date": "2026-12-01"}, headers=h).status_code == 200
    c.post(f"/api/investigations/{inv_id}/comments", json={"body": "Check this @analyst"}, headers=h)
    assert any(n["kind"] == "mention" for n in c.get("/api/notifications", headers=H(c, "analyst")).json())
    tok = c.post(f"/api/investigations/{inv_id}/share", json={"mode": "link"}, headers=h).json()["token"]
    assert c.get(f"/api/shared/{tok}").json()["read_only"]
    c.delete(f"/api/investigations/{inv_id}/share/{tok}", headers=h); assert c.get(f"/api/shared/{tok}").status_code == 404
    # actions, outcome monitor, conclude -> memory
    aid = c.post(f"/api/investigations/{inv_id}/actions", json={"title": "Expedite replenishment"}, headers=h).json()["id"]
    c.patch(f"/api/actions/{aid}", json={"status": "done"}, headers=h)
    assert c.get(f"/api/investigations/{inv_id}/outcome-monitor", headers=h).json()["action_completed"]
    c.patch(f"/api/investigations/{inv_id}", json={"status": "concluded"}, headers=h)
    assert any(m["investigation_id"] == inv_id for m in c.get("/api/memory/issues?q=stockout", headers=h).json())
    assert c.post(f"/api/investigations/{inv_id}/workflow", headers=h).json()["id"]
    # delete conversation cascades to investigation state (CON-008)
    assert c.delete(f"/api/conversations/{cid}", headers=h).json()["investigations_deleted"] >= 1
    assert c.get(f"/api/investigations/{inv_id}", headers=h).status_code == 404


def test_rbac_and_row_level_security(c):
    ex = H(c, "exec")
    assert c.post("/api/tools/price_optimization", json={"product_name": "Fizzo Cola"}, headers=ex).status_code == 403
    n = H(c, "rm_north")
    r = c.post("/api/tools/compare_periods", json={"metric": "revenue", "period": "last_4_weeks", "group_by": ["region"]}, headers=n).json()
    assert [x["region"] for x in r["rows"]] == ["North"] and r["meta"]["policy"]["row_level_security"]
    assert c.post("/api/tools/query_metric", json={"metric": "revenue", "filters": {"region": ["South"]}}, headers=n).status_code == 403
    assert c.get("/api/governance/audit", headers=H(c, "analyst")).status_code == 403
    assert c.get("/api/governance/audit", headers=H(c, "auditor")).status_code == 200


def test_governance_pulse_and_ops(c):
    h = H(c)
    r = c.put("/api/governance/metrics/revenue", json={"description": "Net revenue after discounts and returns.", "status": "certified"}, headers=H(c, "steward")).json()
    assert r["version"] == 2
    c.put("/api/governance/metrics/units", json={"description": "x", "status": "deprecated"}, headers=H(c, "steward"))
    assert c.post("/api/tools/query_metric", json={"metric": "units"}, headers=h).status_code == 400
    c.put("/api/governance/metrics/units", json={"description": "Consumer units sold.", "status": "certified"}, headers=H(c, "steward"))
    sc = c.post("/api/pulse/scan?auto_create=true", headers=h).json()
    assert sc["issues"] and sc["created_investigations"]
    assert c.get("/api/pulse/overview", headers=h).json()["facts"]["kpis"]
    t = c.get("/api/admin/telemetry", headers=h).json(); assert t["tools"]["total_calls"] > 5
    assert c.get("/api/integrations", headers=h).json()["connectors"]
    assert c.get("/api/governance/lineage", headers=h).json()["metrics"]
    assert c.post("/api/tools/data_quality_check", json={}, headers=h).json()["facts"]["issues"]
