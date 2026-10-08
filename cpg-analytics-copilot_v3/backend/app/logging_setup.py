"""OBS-003 structured JSON logging with request correlation (OBS-001)."""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default="-")


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


def setup():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [h]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)


def log(name, level, msg, **ctx):
    logging.getLogger(name).log(level, msg, extra={"ctx": ctx})
