"""State store (SQLite) + analytics engine (SQLAlchemy: SQLite by default, Azure SQL via URL)."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import bindparam, create_engine, text

from .config import settings


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def uid(prefix=""):
    return prefix + uuid.uuid4().hex[:10]


def _ser(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (datetime, date, pd.Timestamp)):
        return o.isoformat()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serializable: {type(o)}")


def jd(o):
    return json.dumps(o, default=_ser)


def jl(s, default=None):
    return json.loads(s) if s else default


@contextmanager
def conn():
    c = sqlite3.connect(settings.state_db, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def q(sql, params=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def q1(sql, params=()):
    r = q(sql, params)
    return r[0] if r else None


def x(sql, params=()):
    with conn() as c:
        c.execute(sql, params)


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE, display_name TEXT, role TEXT, scope_json TEXT, pw_hash TEXT, salt TEXT);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, user_id TEXT, title TEXT, archived INTEGER DEFAULT 0, context_json TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, payload_json TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_msg_conv ON messages(conversation_id, created_at);
CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, owner_type TEXT, owner_id TEXT, label TEXT, message_id TEXT, tool TEXT, args_json TEXT, result_json TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS ix_ev_owner ON evidence(owner_type, owner_id);
CREATE TABLE IF NOT EXISTS investigations(id TEXT PRIMARY KEY, user_id TEXT, conversation_id TEXT, title TEXT, observation TEXT, status TEXT, priority TEXT, owner TEXT, due_date TEXT, source TEXT, issue_id TEXT, data_json TEXT, created_at TEXT, updated_at TEXT, concluded_at TEXT);
CREATE TABLE IF NOT EXISTS comments(id TEXT PRIMARY KEY, investigation_id TEXT, user_id TEXT, body TEXT, mentions_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, body TEXT, link TEXT, read INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS shares(token TEXT PRIMARY KEY, investigation_id TEXT, created_by TEXT, permission TEXT, expires_at TEXT, created_at TEXT, revoked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS issue_memory(id TEXT PRIMARY KEY, investigation_id TEXT, title TEXT, signature_json TEXT, text TEXT, hypotheses_json TEXT, root_cause TEXT, outcome_json TEXT, source TEXT, occurred_on TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS outcomes(id TEXT PRIMARY KEY, investigation_id TEXT, action TEXT, result TEXT, metric_before REAL, metric_after REAL, notes TEXT, created_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, investigation_id TEXT, title TEXT, description TEXT, owner TEXT, due_date TEXT, status TEXT, created_by TEXT, created_at TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, ts TEXT, request_id TEXT, user_id TEXT, role TEXT, action TEXT, detail_json TEXT);
CREATE TABLE IF NOT EXISTS llm_calls(id TEXT PRIMARY KEY, ts TEXT, request_id TEXT, model TEXT, purpose TEXT, latency_ms REAL, status TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, error TEXT);
CREATE TABLE IF NOT EXISTS tool_calls(id TEXT PRIMARY KEY, ts TEXT, request_id TEXT, user_id TEXT, tool TEXT, latency_ms REAL, status TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS metric_defs(key TEXT PRIMARY KEY, name TEXT, description TEXT, formula_text TEXT, unit TEXT, owner TEXT, version INTEGER, status TEXT, updated_at TEXT, updated_by TEXT);
CREATE TABLE IF NOT EXISTS metric_history(id TEXT PRIMARY KEY, key TEXT, version INTEGER, description TEXT, status TEXT, changed_by TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS workflow_tasks(id TEXT PRIMARY KEY, investigation_id TEXT, title TEXT, system TEXT, external_ref TEXT, status TEXT, payload_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS radar_issues(id TEXT PRIMARY KEY, data_json TEXT, score REAL, status TEXT, investigation_id TEXT, scan_id TEXT, detected_at TEXT);
"""


def init_state():
    with conn() as c:
        c.executescript(SCHEMA)


# ---------------- analytics engine ----------------
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.analytics_url, pool_pre_ping=True)
    return _engine


def fetch_df(sql, params=None, expanding=()):
    stmt = text(sql)
    if expanding:
        stmt = stmt.bindparams(*[bindparam(p, expanding=True) for p in expanding])
    with engine().connect() as c:
        return pd.read_sql(stmt, c, params=params or {})
