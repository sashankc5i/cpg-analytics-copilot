"""Exercises the Groq tool-calling loop with a fake client (no network)."""
import json, os, sys, tempfile
d = tempfile.mkdtemp()
os.environ.update(STATE_DB=f"{d}/state.db", ANALYTICS_DB_URL=f"sqlite:///{d}/cpg.db", GROQ_API_KEY="")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.main import app
from app.llm import llm


def tc(name, args, i="call_1"):
    return NS(id=i, function=NS(name=name, arguments=json.dumps(args)))


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, calls = self.script.pop(0)
        return NS(choices=[NS(message=NS(content=content, tool_calls=calls))], usage=NS(prompt_tokens=100, completion_tokens=20))


def login(c):
    return {"Authorization": "Bearer " + c.post("/api/auth/login", json={"username": "admin", "password": "demo123"}).json()["token"]}


def test_tool_loop_grounding_and_telemetry():
    with TestClient(app) as c:
        h = login(c)
        llm.client = Fake([(None, [tc("compare_periods", {"metric": "revenue", "period": "last_4_weeks", "group_by": "region"})]),
                           ("Revenue fell 7.5% [E1]; South was the biggest mover. Total lost was $999.9M.", None)])
        r = c.post("/api/chat", json={"message": "How did regions do?"}, headers=h).json()["assistant_message"]
        assert r["payload"]["mode"] == "groq" and r["payload"]["evidence"][0]["label"] == "E1"
        assert "999.9M" in " ".join(r["payload"]["grounding"]["unverified"])      # hallucinated number flagged
        assert "7.5%" not in " ".join(r["payload"]["grounding"]["unverified"])   # real number verified
        sent = llm.client.calls[0]
        assert any(t["function"]["name"] == "compare_periods" for t in sent["tools"]) and "NEVER compute" in sent["messages"][0]["content"]
        assert any(m["role"] == "tool" for m in llm.client.calls[1]["messages"])   # tool result fed back to the model
        assert c.get("/api/admin/telemetry", headers=h).json()["llm"]["total_calls"] >= 2


def test_validation_error_is_fed_back_and_clarification():
    with TestClient(app) as c:
        h = login(c)
        llm.client = Fake([(None, [tc("compare_periods", {"metric": "revenue", "period": "last_4_weeks", "filters": {"region": ["Atlantis"]}})]),
                           (None, [tc("request_clarification", {"question": "Which region did you mean?", "options": ["North", "South"]}, "call_2")])])
        r = c.post("/api/chat", json={"message": "revenue in atlantis"}, headers=h).json()["assistant_message"]
        tool_msg = json.loads(next(m["content"] for m in llm.client.calls[1]["messages"] if m["role"] == "tool"))
        assert tool_msg["kind"] == "validation" and "Valid values" in tool_msg["error"]
        assert r["payload"]["clarification"]["options"] == ["North", "South"]


def test_llm_failure_falls_back_to_offline():
    with TestClient(app) as c:
        h = login(c)
        class Boom:
            chat = NS(completions=NS(create=lambda **kw: (_ for _ in ()).throw(RuntimeError("429 rate limit"))))
        llm.client = Boom()
        r = c.post("/api/chat", json={"message": "revenue by region last month"}, headers=h).json()["assistant_message"]
        assert r["payload"]["mode"].startswith("offline") and r["payload"]["evidence"]
        assert c.get("/api/admin/telemetry", headers=h).json()["llm"]["failures"] >= 1
    llm.client = None
