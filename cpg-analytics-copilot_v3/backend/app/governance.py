"""GOV-004 metric governance, GOV-005 audit trail."""
from . import semantic as S
from .db import jd, now, q, q1, uid, x
from .logging_setup import request_id_var

OWNERS = {"sales": "Commercial Finance", "inventory": "Supply Chain"}


def audit(user, action, detail=None):
    x("INSERT INTO audit VALUES(?,?,?,?,?,?,?)", (uid("a_"), now(), request_id_var.get(), (user or {}).get("id", "system"), (user or {}).get("role", "system"), action, jd(detail or {})))


def seed_metrics():
    for k, m in S.METRICS.items():
        if not q1("SELECT key FROM metric_defs WHERE key=?", (k,)):
            x("INSERT INTO metric_defs VALUES(?,?,?,?,?,?,?,?,?,?)", (k, m["name"], m["desc"], m["formula"], m["unit"], OWNERS[m["source"]], 1, "certified", now(), "system"))
            x("INSERT INTO metric_history VALUES(?,?,?,?,?,?,?)", (uid("mh_"), k, 1, m["desc"], "certified", "system", now()))
    refresh_status()


def refresh_status():
    S.METRIC_STATUS.clear()
    S.METRIC_STATUS.update({r["key"]: r["status"] for r in q("SELECT key,status FROM metric_defs")})


def update_metric(user, key, description, status, owner=None):
    cur = q1("SELECT * FROM metric_defs WHERE key=?", (key,))
    if not cur:
        return None
    v = cur["version"] + (1 if description != cur["description"] else 0)
    x("UPDATE metric_defs SET description=?, status=?, owner=?, version=?, updated_at=?, updated_by=? WHERE key=?", (description, status, owner or cur["owner"], v, now(), user["username"], key))
    x("INSERT INTO metric_history VALUES(?,?,?,?,?,?,?)", (uid("mh_"), key, v, description, status, user["username"], now()))
    refresh_status(); audit(user, "metric.update", {"key": key, "version": v, "status": status})
    return q1("SELECT * FROM metric_defs WHERE key=?", (key,))
