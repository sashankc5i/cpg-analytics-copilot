"""GOV-001/002/003: identity (local JWT or OIDC), RBAC, row-level security."""
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException

from .config import settings
from .db import jd, jl, q, q1, uid, x

CORE = ["query_metric", "compare_periods", "top_bottom", "trend_analysis", "variance_analysis", "drilldown", "performance_scorecard", "business_health_overview", "detect_business_issues",
        "business_timeline", "data_quality_check", "driver_decomposition", "price_volume_mix", "anomaly_detection", "start_investigation", "request_clarification", "recall_similar_issues"]
ADV = ["promotion_analysis", "stockout_analysis", "assortment_analysis", "customer_cohorts", "competitor_signals", "price_elasticity"]
DEC = ["demand_forecast", "inventory_optimization", "price_optimization"]
ALL_FEATURES = {"chat", "investigate", "share", "assign", "comment", "audit_view", "metric_admin", "telemetry_view", "integrations", "user_admin", "replay", "export"}
ROLES = {
    "admin": {"tools": CORE + ADV + DEC, "features": ALL_FEATURES},
    "analyst": {"tools": CORE + ADV + DEC, "features": {"chat", "investigate", "share", "comment", "replay", "export"}},
    "manager": {"tools": CORE + ADV + DEC, "features": {"chat", "investigate", "share", "assign", "comment", "replay", "export", "integrations"}},
    "exec": {"tools": CORE + ["promotion_analysis", "stockout_analysis", "competitor_signals", "demand_forecast"], "features": {"chat", "investigate", "share", "comment", "replay", "export"}},
    "steward": {"tools": CORE, "features": {"chat", "comment", "metric_admin", "replay"}},
    "auditor": {"tools": [], "features": {"audit_view", "replay", "export"}},
}
DEMO = [("admin", "Alex Admin", "admin", {}), ("analyst", "Ana Analyst", "analyst", {}), ("manager", "Mo Manager", "manager", {}), ("exec", "Eva Executive", "exec", {}),
        ("steward", "Sam Steward", "steward", {}), ("auditor", "Audi Auditor", "auditor", {}), ("rm_north", "Nora North (Regional Mgr)", "manager", {"region": ["North"]})]


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 60000).hex()


def seed_users():
    for u, n, r, sc in DEMO:
        if not q1("SELECT id FROM users WHERE username=?", (u,)):
            salt = uid()
            x("INSERT INTO users VALUES(?,?,?,?,?,?,?)", ("u_" + u, u, n, r, jd(sc), _hash(settings.demo_password, salt), salt))


def user_public(u):
    return {"id": u["id"], "username": u["username"], "display_name": u["display_name"], "role": u["role"], "scope": jl(u["scope_json"], {}),
            "tools": ROLES[u["role"]]["tools"], "features": sorted(ROLES[u["role"]]["features"])}


def login(username, password):
    u = q1("SELECT * FROM users WHERE username=?", (username,))
    if settings.auth_mode != "local" or not u or not hmac.compare_digest(_hash(password, u["salt"]), u["pw_hash"]):
        raise HTTPException(401, "Invalid username or password.")
    tok = jwt.encode({"sub": u["id"], "role": u["role"], "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_ttl_min)}, settings.jwt_secret, algorithm="HS256")
    return {"token": tok, "user": user_public(u)}


def _oidc_user(token):
    jc = jwt.PyJWKClient(settings.oidc_jwks_url)
    key = jc.get_signing_key_from_jwt(token).key
    c = jwt.decode(token, key, algorithms=["RS256"], audience=settings.oidc_audience or None, issuer=settings.oidc_issuer or None)
    uname = c.get("preferred_username") or c.get("email") or c["sub"]
    rmap = dict(p.split("=") for p in settings.oidc_role_map.split(",") if "=" in p)
    role = next((rmap[g] for g in (c.get("roles") or c.get("groups") or []) if g in rmap), "analyst")
    u = q1("SELECT * FROM users WHERE username=?", (uname,))
    scope = c.get("cpg_scope") or {}
    if not u:
        x("INSERT INTO users VALUES(?,?,?,?,?,?,?)", ("u_" + uid(), uname, c.get("name", uname), role, jd(scope), "", ""))
        u = q1("SELECT * FROM users WHERE username=?", (uname,))
    return u


def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required.")
    tok = authorization.split(" ", 1)[1]
    try:
        if settings.auth_mode == "oidc":
            u = _oidc_user(tok)
        else:
            c = jwt.decode(tok, settings.jwt_secret, algorithms=["HS256"]); u = q1("SELECT * FROM users WHERE id=?", (c["sub"],))
    except Exception:
        raise HTTPException(401, "Invalid or expired token.")
    if not u:
        raise HTTPException(401, "Unknown user.")
    return user_public(u)


def require(feature):
    def dep(user=Depends(current_user)):
        if feature not in user["features"]:
            raise HTTPException(403, f"Your role ({user['role']}) does not include '{feature}'.")
        return user
    return dep
