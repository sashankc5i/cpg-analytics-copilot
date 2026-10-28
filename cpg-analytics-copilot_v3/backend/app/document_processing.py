"""Extraction, retrieval, chunking, and cited document chat helpers."""
import io
import re
import time
from datetime import datetime, timezone

from fastapi import HTTPException

from . import db
from .llm import LLMUnavailable, llm

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 300


def extract_pdf(data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF exceeds the 15 MiB upload limit.")
    try:
        import fitz
        import pdfplumber
    except ImportError as exc:
        raise HTTPException(503, "PDF support requires pymupdf and pdfplumber.") from exc
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            tables = []
            for table in page.extract_tables() or []:
                tables.append("\n[TABLE]\n" + "\n".join(" | ".join(str(c or "") for c in row) for row in table) + "\n[/TABLE]")
            pages.append(f"[Page {number}]\n{text}" + "".join(tables))
    # OCR every page so diagrams and screenshots are included alongside native text/tables.
    try:
        import pytesseract
        from PIL import Image
        document = fitz.open(stream=data, filetype="pdf")
        for index in range(len(pages)):
            pix = document[index].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            image_text = pytesseract.image_to_string(image).strip()
            if image_text:
                pages[index] += "\n[OCR]\n" + image_text
    except Exception:
        pass
    result = "\n\n".join(pages).strip()
    if not result:
        raise HTTPException(422, "No text or tables could be extracted from this PDF.")
    return result


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    if size < 1 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and overlap must be smaller than size")
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append({"index": len(chunks), "start": start, "end": end, "size": end - start, "text": text[start:end]})
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def fetch_documents(document_ids):
    if not document_ids:
        return []
    marks = ",".join("?" for _ in document_ids)
    rows = db.q(f"SELECT id,title,content,source,updated_at FROM knowledge_documents WHERE id IN ({marks})", tuple(document_ids))
    found = {row["id"] for row in rows}
    missing = set(document_ids) - found
    if missing:
        raise HTTPException(404, f"Unknown document IDs: {', '.join(sorted(missing))}")
    return rows


def retrieve_documents(query, limit=8):
    tokens = list(dict.fromkeys(re.findall(r"[\w-]{3,}", query.lower())))[:8]
    if not tokens:
        return []
    where = " OR ".join("lower(title || ' ' || content) LIKE ?" for _ in tokens)
    params = tuple(f"%{token}%" for token in tokens)
    return db.q(f"SELECT id,title,content,source,updated_at FROM knowledge_documents WHERE {where} ORDER BY updated_at DESC LIMIT ?", (*params, limit))


def concatenate_documents(documents):
    return "\n\n".join(f"[DocID:{d['id']}] {d['title']}\n{d['content']}" for d in documents)


def select_sources(documents, database_evidence=None):
    """Rank the available document and analytics evidence, exposing the reason."""
    def evidence_updated_at(evidence):
        freshness = evidence.get("freshness") or {}
        timestamps = [source.get("last_refreshed") or source.get("refreshed") for source in freshness.get("sources", [])]
        timestamps = [stamp for stamp in timestamps if stamp]
        return max(timestamps, default="")

    dated = sorted(documents, key=lambda d: (d.get("updated_at") or "", d.get("source") != "upload"), reverse=True)
    selected = dated[0] if dated else None
    candidates = [{"source": "document", "document_id": d["id"], "title": d["title"], "updated_at": d.get("updated_at"),
                   "confidence": round(0.9 if d is selected else 0.75, 2)} for d in dated]
    for evidence in (database_evidence or []):
        candidates.append({"source": "database", "label": evidence.get("label"), "title": evidence.get("headline"),
                           "updated_at": evidence_updated_at(evidence), "confidence": 0.85})
    picked = {"source": "document", "document_id": selected["id"]} if selected else None
    reason = "The newest available document is selected; confidence is a retrieval ranking signal, not a calibrated probability."
    if database_evidence:
        newest_doc = max((d.get("updated_at") or "" for d in documents), default="")
        newest_db = max((evidence_updated_at(e) for e in database_evidence), default="")
        if newest_db and newest_db >= newest_doc:
            picked = {"source": "database", "label": database_evidence[0].get("label")}
            reason = "The governed analytics evidence was selected because its refresh timestamp is at least as recent as the uploaded document; both sources are shown so the difference can be reviewed."
        else:
            reason = "The uploaded document was selected because it is newer than the available analytics evidence; the database evidence is also shown for comparison."
    return {"selected": picked, "candidates": candidates, "reason": reason}


def answer_query(query, documents, database_evidence=None):
    if not documents:
        raise HTTPException(422, "Provide at least one document ID or upload a PDF.")
    started = time.perf_counter()
    prompt_context = concatenate_documents(documents)
    selection = select_sources(documents, database_evidence)
    db_context = "\n\nGoverned analytics evidence (cite its [E#] label):\n" + str(database_evidence)[:24000] if database_evidence else ""
    try:
        message = llm.chat([
            {"role": "system", "content": "Write a concise source comparison report with these headings: Summary, Document evidence, CPG data evidence, Source selected and why, and Limitations. Answer only from supplied evidence. Cite every document claim inline with [DocID:<id>] and every CPG claim with its [E#] label. Compare dates and definitions; do not claim two values conflict unless they measure the same thing over comparable periods. State when CPG evidence is unavailable or does not cover the document period. Follow source_selection when choosing a source for a shared fact and explain the freshness/evidence-quality reason. Do not invent facts or citations."},
            {"role": "user", "content": f"Prepare a source comparison report for this question: {query[:4000]}\nSource selection: {selection}\n\nDocuments:\n{prompt_context[:50000]}{db_context}"},
        ], purpose="document_chat", temperature=0.1, max_tokens=1400)
        answer = message.content or ""
        mode = "llm"
    except LLMUnavailable:
        # Keep document chat usable in local/demo installs without a configured LLM.
        selected_id = selection.get("selected", {}).get("document_id") if selection.get("selected") else None
        selected = next((doc for doc in documents if doc["id"] == selected_id), documents[0])
        terms = {term for term in re.findall(r"[\w-]{3,}", query.lower()) if term not in {"what", "when", "where", "which", "does", "this", "that", "from", "with", "about", "have", "into", "show", "tell"}}
        passages = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", selected["content"]) if len(part.strip()) > 25]
        ranked = sorted(passages, key=lambda part: sum(term in part.lower() for term in terms), reverse=True)
        useful = [part for part in ranked if not terms or any(term in part.lower() for term in terms)][:4]
        if not useful:
            useful = passages[:3]
        document_findings = "\n".join(f"- {part} [DocID:{selected['id']}]" for part in useful)
        if database_evidence:
            db_passages = [e for e in database_evidence if e.get("headline") or e.get("facts")]
            database_findings = "\n".join(f"- {e.get('headline') or e.get('facts')} [{e.get('label')}]" for e in db_passages[:3]) or "- No comparable CPG evidence was returned."
        else:
            database_findings = "- No comparable CPG evidence was returned for this request."
        answer = ("## Source comparison report (local extractive mode)\n\n"
                  f"### Summary\nDocument findings are shown with citations. Check the date coverage and definitions before treating CPG values as directly comparable.\n\n"
                  f"### Document evidence\n{document_findings}\n\n### CPG data evidence\n{database_findings}\n\n"
                  f"### Source selected and why\n{selection.get('selected')}: {selection['reason']}\n\n"
                  "### Limitations\nLocal mode selects relevant document passages and reports available analytics evidence; it does not establish causality or equivalence between different periods or metric definitions.")
        mode = "extractive_offline"
    return {"answer": answer, "mode": mode, "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "citations": sorted(set(re.findall(r"\[DocID:([^\]]+)\]", answer))), "source_selection": selection}

