"""OBS-003 structured JSON logging with request correlation (OBS-001)."""
import contextvars
import json
import logging
import sys
from collections import deque
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default="-")
_recent = deque(maxlen=2000)
_sequence = 0


class JsonFormatter(logging.Formatter):
    def format(self, r):
        d = {
            "ts": datetime.fromtimestamp(r.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": r.levelname,
            "component": r.name,
            "msg": r.getMessage(),
            "request_id": request_id_var.get(),
        }
        d.update(getattr(r, "ctx", {}) or {})
        if r.exc_info:
            d["exc"] = self.formatException(r.exc_info)
        return json.dumps(d, default=str)


class RecentHandler(logging.Handler):
    def emit(self, record):
        global _sequence
        try:
            _sequence += 1
            _recent.append((_sequence, record.levelno, self.format(record)))
        except Exception:
            self.handleError(record)


def recent_logs(level="INFO", limit=200):
    threshold = getattr(logging, level.upper(), logging.INFO)
    return [(sequence, line) for sequence, number, line in list(_recent) if number >= threshold][-limit:]


def logs_after(sequence, level="INFO", limit=200):
    threshold = getattr(logging, level.upper(), logging.INFO)
    return [(index, line) for index, number, line in list(_recent) if index > sequence and number >= threshold][-limit:]


def setup():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    recent = RecentHandler()
    recent.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h, recent]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)


def log(name, level, msg, **ctx):
    logging.getLogger(name).log(level, msg, extra={"ctx": ctx})
