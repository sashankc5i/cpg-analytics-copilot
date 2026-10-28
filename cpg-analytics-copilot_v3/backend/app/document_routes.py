"""User-authenticated document chat endpoints."""
import time
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import db
from .document_processing import answer_query, extract_pdf, fetch_documents, retrieve_documents
from .security import current_user

router = APIRouter()


def _save_document(file: UploadFile, content: str, user, file_data: bytes):
    document_id = db.uid("upload_")
    title = (file.filename or "Uploaded PDF")[:200]
    updated_at = db.now()
    db.x("INSERT INTO knowledge_documents VALUES(?,?,?,?,?,?)", (document_id, title, content, "upload", updated_at, db.jd({"uploaded_by": user["id"], "uploaded_by_name": user.get("display_name")})))
    db.x("INSERT INTO knowledge_document_files(document_id,file_data,content_type,filename) VALUES(?,?,?,?)", (document_id, file_data, "application/pdf", title))
    return {"id": document_id, "title": title, "source": "upload", "updated_at": updated_at}


@router.get("/api/documents")
def list_documents(search: str = Query("", max_length=100), user=Depends(current_user)):
    term = search.strip()
    if term:
        rows = db.q("SELECT d.id,d.title,d.source,d.updated_at,EXISTS(SELECT 1 FROM knowledge_document_files f WHERE f.document_id=d.id) AS file_available FROM knowledge_documents d WHERE d.title LIKE ? OR d.content LIKE ? ORDER BY d.updated_at DESC LIMIT 100", (f"%{term}%", f"%{term}%"))
    else:
        rows = db.q("SELECT d.id,d.title,d.source,d.updated_at,EXISTS(SELECT 1 FROM knowledge_document_files f WHERE f.document_id=d.id) AS file_available FROM knowledge_documents d ORDER BY d.updated_at DESC LIMIT 100")
    return {"items": rows, "shared": True}


@router.get("/api/documents/{document_id}")
def get_document(document_id: str, user=Depends(current_user)):
    row = db.q1("SELECT id,title,content,source,updated_at FROM knowledge_documents WHERE id=?", (document_id,))
    if not row:
        raise HTTPException(404, "Document not found.")
    return row


@router.get("/api/documents/{document_id}/file")
def get_document_file(document_id: str, user=Depends(current_user)):
    row = db.q1("SELECT f.file_data,f.content_type,f.filename FROM knowledge_document_files f JOIN knowledge_documents d ON d.id=f.document_id WHERE f.document_id=?", (document_id,))
    if not row:
        raise HTTPException(404, "Original PDF is unavailable for this document.")
    filename = quote(row["filename"] or "document.pdf", safe="")
    return Response(content=row["file_data"], media_type=row["content_type"], headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"})


@router.post("/api/documents/upload", status_code=201)
async def upload_document(file: UploadFile = File(...), user=Depends(current_user)):
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Upload must be a PDF.")
    file_data = await file.read(15 * 1024 * 1024 + 1)
    content = extract_pdf(file_data)
    return _save_document(file, content, user, file_data)


class DocumentChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(default_factory=list, max_length=20)


@router.post("/api/document-chat")
def document_chat(body: DocumentChatRequest, user=Depends(current_user)):
    docs = fetch_documents(body.document_ids) if body.document_ids else retrieve_documents(body.query)
    started = time.perf_counter()
    result = answer_query(body.query, docs)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result


@router.post("/api/document-chat/upload")
async def document_chat_upload(query: str = Form(...), file: UploadFile = File(...), user=Depends(current_user)):
    if file.content_type != "application/pdf" and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Upload must be a PDF.")
    data = await file.read(15 * 1024 * 1024 + 1)
    content = extract_pdf(data)
    started = time.perf_counter()
    uploaded = _save_document(file, content, user, data)
    uploaded["content"] = content
    documents = retrieve_documents(query)
    if all(item["id"] != document_id for item in documents):
        documents.insert(0, uploaded)
    result = answer_query(query, documents)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result
