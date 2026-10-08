"""Golden-question evaluation: does a question route to the expected governed tool and succeed?
Run:  python tests/eval_questions.py            (offline planner)
      GROQ_API_KEY=... python tests/eval_questions.py   (measures the real LLM routing)
Not a pytest module (name does not start with test_)."""
import os, sys, tempfile
d = tempfile.mkdtemp()
os.environ.setdefault("STATE_DB", f"{d}/state.db"); os.environ.setdefault("ANALYTICS_DB_URL", f"sqlite:///{d}/cpg.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app.main import app

GOLDEN = [  # (question, set of acceptable tools)
    ("How is the business performing?", {"business_health_overview"}),
    ("What was revenue by region last month?", {"query_metric", "compare_periods", "performance_scorecard"}),
    ("Top 5 products by units last quarter", {"top_bottom"}),
    ("Bottom 3 channels by revenue", {"top_bottom"}),
    ("Compare revenue Q2 2026 vs Q1 2026 by category", {"compare_periods", "performance_scorecard"}),
    ("Revenue trend by month for Beverages", {"trend_analysis"}),
    ("What is the margin by segment?", {"query_metric", "performance_scorecard"}),
    ("Show stockouts by region", {"stockout_analysis"}),
    ("Which promotions delivered the best lift?", {"promotion_analysis"}),
    ("Did the Crunch Bites promotion cannibalise Crunch Minis?", {"promotion_analysis"}),
    ("Any anomalies in revenue by region?", {"anomaly_detection"}),
    ("Forecast units for the next 8 weeks", {"demand_forecast"}),
    ("What is the price elasticity of Sparkle Detergent?", {"price_elasticity"}),
    ("Optimise price for Sparkle Detergent", {"price_optimization"}),
    ("Safety stock recommendations", {"inventory_optimization"}),
    ("Show customer cohort retention", {"customer_cohorts"}),
    ("What do competitors do in Personal Care?", {"competitor_signals"}),
    ("Assortment analysis", {"assortment_analysis"}),
    ("Break down Beverages by brand", {"drilldown"}),
    ("Price volume mix last 12 weeks", {"price_volume_mix"}),
    ("What drove the change in revenue for South?", {"driver_decomposition", "start_investigation"}),
    ("Why did South revenue decline last 4 weeks?", {"start_investigation"}),
    ("Any data quality issues?", {"data_quality_check"}),
    ("What issues need attention?", {"detect_business_issues"}),
    ("Show the timeline", {"business_timeline"}),
    ("Variance vs prior year for units", {"variance_analysis", "compare_periods"}),
    ("Have we seen something similar before?", {"recall_similar_issues"}),
    ("hello", {"request_clarification"}),
]

if __name__ == "__main__":
    ok = 0; fails = []
    with TestClient(app) as c:
        h = {"Authorization": "Bearer " + c.post("/api/auth/login", json={"username": "admin", "password": "demo123"}).json()["token"]}
        for q, exp in GOLDEN:
            p = c.post("/api/chat", json={"message": q}, headers=h).json()["assistant_message"]["payload"]
            used = {t["name"] for t in p["tools"]} | ({"request_clarification"} if p["clarification"] else set())
            good = bool(used & exp) and all(t["status"] == "ok" for t in p["tools"]) and p["grounding"]["unverified"] == []
            ok += good
            if not good: fails.append((q, sorted(used), p["grounding"]["unverified"]))
    print(f"mode={'groq' if os.getenv('GROQ_API_KEY') else 'offline'}  passed {ok}/{len(GOLDEN)} ({ok / len(GOLDEN):.0%})")
    for f in fails: print("FAIL", f)
