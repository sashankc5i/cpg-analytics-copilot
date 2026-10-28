"""Admin-only document administration, evaluation, and diagnostics."""
from enum import Enum
import asyncio
import base64
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import MetaData, String, Table, cast, func, inspect, or_, select

from . import db, evaluation, logging_setup
from .analytics.core import reset_caches
from .document_processing import chunk_text, extract_pdf
from .security import require

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require("user_admin"))])


class TableName(str, Enum):
    knowledge_documents = "knowledge_documents"
    chat_logs = "messages"
    evaluation_results = "evaluation_results"


def _analytics_inventory(schema: str | None = None):
    engine = db.engine()
    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema=schema)
    view_names = inspector.get_view_names(schema=schema)
    inventory = []
    for name, kind in [(name, "table") for name in table_names] + [(name, "view") for name in view_names]:
        columns = inspector.get_columns(name, schema=schema)
        inventory.append({"name": name, "schema": schema, "kind": kind,
                          "columns": [{"name": column["name"], "type": str(column["type"])} for column in columns]})
    database = engine.url.database
    database_name = Path(database).name if database and database != ":memory:" else (database or "analytics")
    return engine, {"database": database_name, "dialect": engine.dialect.name, "tables": inventory}


def _analytics_table(engine, table_name: str, schema: str | None):
    try:
        inspector = inspect(engine)
        if schema and schema not in inspector.get_schema_names():
            raise HTTPException(404, "Analytics schema not found.")
        available = set(inspector.get_table_names(schema=schema)) | set(inspector.get_view_names(schema=schema))
        if table_name not in available:
            raise HTTPException(404, "Analytics table not found.")
        return Table(table_name, MetaData(), schema=schema, autoload_with=engine)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Analytics database is unavailable.") from exc


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"base64": base64.b64encode(bytes(value)).decode("ascii")}
    return value


@router.get("/analytics/tables")
def analytics_tables(schema: str | None = Query(None, max_length=128)):
    try:
        _, inventory = _analytics_inventory(schema)
        return inventory
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, "Analytics database is unavailable.") from exc


@router.get("/analytics/data")
def analytics_data(table: str = Query(min_length=1, max_length=128), schema: str | None = Query(None, max_length=128),
                   page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), search: str | None = Query(None, max_length=100)):
    try:
        engine = db.engine()
        reflected = _analytics_table(engine, table, schema)
        statement = select(reflected)
        count_statement = select(func.count()).select_from(reflected)
        searchable = [column for column in reflected.columns if isinstance(column.type, String)]
        if search and searchable:
            criteria = or_(*(cast(column, String).ilike(f"%{search.strip()}%") for column in searchable))
            statement = statement.where(criteria)
            count_statement = count_statement.where(criteria)
        primary_key = list(reflected.primary_key.columns)
        order_columns = primary_key or list(reflected.columns)[:1]
        if order_columns:
            statement = statement.order_by(*order_columns)
        statement = statement.limit(page_size).offset((page - 1) * page_size)
        with engine.connect() as connection:
            total = connection.execute(count_statement).scalar_one()
            rows = connection.execute(statement).mappings().all()
        return {"table": table, "schema": schema, "page": page, "page_size": page_size, "total": total,
                "columns": [column.name for column in reflected.columns],
                "items": [{key: _json_value(value) for key, value in row.items()} for row in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Could not read analytics database records.") from exc


@router.get("/data/{table}")
def admin_data(table: TableName, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), search: str | None = None, conversation_id: str | None = None):
    name = table.value
    conditions, params = [], []
    if search and name == "knowledge_documents":
        conditions.append("(title LIKE ? OR content LIKE ?)"); params.extend([f"%{search[:100]}%"] * 2)
    if conversation_id and name in ("messages", "evaluation_results"):
        conditions.append("conversation_id=?"); params.append(conversation_id)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    total = db.q1(f"SELECT COUNT(*) AS n FROM {name}{where}", tuple(params))["n"]
    rows = db.q(f"SELECT * FROM {name}{where} ORDER BY " + ("updated_at" if name == "knowledge_documents" else "created_at") + " DESC LIMIT ? OFFSET ?", (*params, page_size, (page - 1) * page_size))
    return {"table": table.value, "page": page, "page_size": page_size, "total": total, "items": rows}


@router.post("/evaluations/run", status_code=202)
def run_evaluations(background: BackgroundTasks, limit: int = Query(100, ge=1, le=1000)):
    background.add_task(evaluation.evaluate_recent, limit)
    return {"status": "scheduled", "limit": limit}


@router.get("/evaluations/summary")
def evaluation_summary():
    summary = evaluation.report()
    recent = db.q("SELECT * FROM evaluation_results ORDER BY created_at DESC LIMIT 100")
    for item in recent:
        item["details"] = db.jl(item.pop("details_json"), {})
    return {"summary": summary, "recent": recent}


@router.get("/logs/stream")
def stream_logs(level: str = Query("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"), limit: int = Query(100, ge=1, le=1000)):
    async def events():
        recent = logging_setup.recent_logs(level, limit)
        cursor = recent[-1][0] if recent else 0
        for _, line in recent:
            yield f"data: {line}\n\n"
        while True:
            pending = logging_setup.logs_after(cursor, level, limit)
            for cursor, line in pending:
                yield f"data: {line}\n\n"
            if not pending:
                yield ": keep-alive\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class Diagnostic(BaseModel):
    command: str = Field(pattern="^(health|cache_clear)$")


@router.post("/diagnostics")
def diagnostic(body: Diagnostic):
    if body.command == "health":
        return {"status": "ok", "state_db": bool(db.q1("SELECT 1 AS ok"))}
    reset_caches()
    return {"status": "ok", "cleared": "analytics core cache"}


@router.post("/chunking")
async def chunking(text: str | None = None, file: UploadFile | None = File(default=None), size: int = Query(3000, ge=100, le=10000), overlap: int = Query(300, ge=0, le=2000)):
    if file:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(415, "Upload must be a PDF.")
        content = extract_pdf(await file.read(15 * 1024 * 1024 + 1))
    elif text is not None:
        content = text[:200000]
    else:
        raise HTTPException(422, "Provide text or a PDF file.")
    try:
        chunks = chunk_text(content, size, overlap)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"total_characters": len(content), "chunk_count": len(chunks), "chunks": chunks}
