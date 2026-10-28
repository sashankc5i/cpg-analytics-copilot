import logging
import threading
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db, governance, logging_setup, memory, security, seed
from .config import ROOT, settings
from .logging_setup import log, request_id_var
from .routes import api
from .document_routes import router as document_router
from .admin_routes import router as admin_router

logging_setup.setup()
_http_metrics = defaultdict(lambda: {"count": 0, "duration_seconds": 0.0})


def _radar_loop():
    from .routes import _scan
    u = {"id": "u_admin", "username": "admin", "role": "admin", "scope": {}, "features": list(security.ALL_FEATURES), "display_name": "Radar"}
    while True:
        time.sleep(settings.radar_interval_min * 60)
        try:
            _scan(u, auto_create=True)
        except Exception as e:
            log("radar", logging.ERROR, "scheduled scan failed", error=repr(e)[:200])


@asynccontextmanager
async def lifespan(app):
    db.init_state()
    if seed.build():
        log("startup", logging.INFO, "synthetic CPG dataset created")
    security.seed_users(); governance.seed_metrics(); memory.seed()
    if settings.radar_interval_min > 0:
        threading.Thread(target=_radar_loop, daemon=True).start()
    log("startup", logging.INFO, "ready", llm="groq" if settings.groq_api_key else "offline", auth=settings.auth_mode)
    yield


app = FastAPI(title="CPG Analytics Copilot", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    tok = request_id_var.set(rid); t0 = time.time()
    try:
        resp = await call_next(request)
    except Exception as e:  # OBS-002: never leak internals
        log("http", logging.ERROR, "unhandled error", path=request.url.path, error=repr(e))
        resp = JSONResponse({"error": "An internal error occurred.", "request_id": rid}, status_code=500)
    resp.headers["X-Request-ID"] = rid
    route = request.scope.get("route")
    label = getattr(route, "path", request.url.path)
    metric = _http_metrics[(request.method, label, str(resp.status_code))]
    metric["count"] += 1
    metric["duration_seconds"] += time.time() - t0
    if request.url.path.startswith("/api"):
        log("http", logging.INFO, "request", method=request.method, path=request.url.path, status=resp.status_code, ms=round((time.time() - t0) * 1000))
    request_id_var.reset(tok)
    return resp


@app.exception_handler(HTTPException)
async def http_exc(request, exc):
    return JSONResponse({"error": exc.detail, "request_id": request_id_var.get()}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def val_exc(request, exc):
    return JSONResponse({"error": "Invalid request: " + "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()[:3]), "request_id": request_id_var.get()}, status_code=422)


app.include_router(api)
app.include_router(document_router)
app.include_router(admin_router)


def metrics_text():
    lines = ["# HELP http_requests_total Total HTTP requests.", "# TYPE http_requests_total counter",
             "# HELP http_request_duration_seconds_sum Total HTTP request duration in seconds.", "# TYPE http_request_duration_seconds_sum counter"]
    for (method, path, status), values in sorted(_http_metrics.items()):
        labels = f'method="{method}",path="{path}",status="{status}"'
        lines.extend((f"http_requests_total{{{labels}}} {values['count']}", f"http_request_duration_seconds_sum{{{labels}}} {values['duration_seconds']:.6f}"))
    return "\n".join(lines) + "\n"


@app.get("/metrics", include_in_schema=False)
def metrics(user=Depends(security.require("user_admin"))):
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(metrics_text(), media_type="text/plain; version=0.0.4; charset=utf-8")


DIST = ROOT.parent / "frontend" / "dist"
if DIST.exists():  # single-process deployment: serve the built React app
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if f.is_file() else DIST / "index.html")
