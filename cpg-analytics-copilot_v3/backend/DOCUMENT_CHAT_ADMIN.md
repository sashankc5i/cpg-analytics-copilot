# Document chat and administration API

All routes are served by the FastAPI backend. Send `Authorization: Bearer <JWT>` for authenticated calls. Admin routes require the `admin` role through the existing `user_admin` feature check. `/metrics` also requires admin authentication because it exposes operational data.

## Document chat

| Method and path | Request | Response | Permission |
| --- | --- | --- | --- |
| `GET /api/documents` | Optional `search` query string. | `{"shared":true,"items":[{"id":"...","title":"...","source":"upload","updated_at":"...","file_available":true}]}` | Any signed-in user; lists the shared document library |
| `GET /api/documents/{document_id}` | Document ID in the path. | Document metadata plus extracted text content. | Any signed-in user; all uploaded documents are shared across users |
| `GET /api/documents/{document_id}/file` | Document ID in the path. | Original PDF bytes (`application/pdf`) for inline preview. | Any signed-in user |
| `POST /api/documents/upload` | Multipart `file` (PDF, max 15 MiB). | `{"id":"...","title":"...","source":"upload","updated_at":"..."}` | Any signed-in user; stores the PDF for shared use |
| `POST /api/document-chat` | JSON: `{"query":"...","document_ids":["doc-1"]}`. IDs may be omitted to search stored documents. | `{"answer":"... [DocID:doc-1]","citations":["doc-1"],"source_selection":{"selected":"doc-1","candidates":[],"reason":"..."},"latency_ms":12.3}` | Authenticated user |
| `POST /api/document-chat/upload` | Multipart `query` and `file` (PDF, max 15 MiB). | Same response shape; uploaded PDF is stored in `knowledge_documents`. | Authenticated user |

The paperclip uploads a PDF. The Library tab lists saved uploads, previews original PDF bytes, and attaches saved documents to chat. Document questions automatically include available governed CPG evidence and return a structured comparison report with `[DocID:<id>]` and `[E#]` citations. Local/demo mode returns a cited report with extractive document findings and available CPG evidence. Four synthetic PDFs are available in `frontend/public/sample-documents/` for manual upload tests.

Document ingestion extracts page text and tables with `pdfplumber`; image-only pages are OCR'd with PyMuPDF, Pillow, and Tesseract when the optional Python package and Tesseract executable are installed. If OCR is unavailable, native text and tables remain available.

## Admin data, evaluation, and diagnostics

The read-only analytics browser adds `GET /admin/analytics/tables` (optional `schema`) and `GET /admin/analytics/data` (required `table`, optional `schema`, `page`, `page_size` up to 200, and text `search`). The table inventory is discovered from the configured analytics database; row reads accept only discovered table and view names. The response includes database name/dialect, columns, total row count, and a page of raw values. In the UI choose **CPG analytics database (cpg.db)** and select `fact_sales`, `fact_inventory`, or another listed table/view.

| Method and path | Request | Response | Permission |
| --- | --- | --- | --- |
| `GET /admin/data/{table}` | Query: `page` (1-based), `page_size` (1–200), optional `search` (documents), `conversation_id` (messages/evaluations). Table is `knowledge_documents`, `chat_logs`, or `evaluation_results`. | `{"table":"...","page":1,"page_size":50,"total":0,"items":[]}` | Admin |
| `POST /admin/evaluations/run` | Query: `limit` (1–1000, default 100). | `{"status":"scheduled","limit":100}`; evaluates recent assistant messages in a background task. | Admin |
| `GET /admin/evaluations/summary` | None. | `{"summary":{"evaluations":0,...},"recent":[]}` | Admin |
| `GET /admin/logs/stream` | Query: `level` (`DEBUG`…`CRITICAL`), `limit` (1–1000). | Server-sent events containing the current recent log snapshot. | Admin |
| `POST /admin/diagnostics` | JSON: `{"command":"health"}` or `{"command":"cache_clear"}`. | Health status or cache-clear status. No arbitrary command execution is supported. | Admin |
| `POST /admin/chunking` | Query `size` / `overlap`; provide query `text` or multipart `file` (PDF). | `{"total_characters":n,"chunk_count":n,"chunks":[{"index":0,"start":0,"end":100,"size":100,"text":"..."}]}` | Admin |
| `GET /metrics` | Prometheus text exposition format. | Request counters and total request duration by method, route, and status. | Admin |

`accuracy` in evaluation results is a citation/evidence grounding heuristic, not a human-verified truth score. Citation correctness measures cited evidence labels that exist in the assistant message payload. Latency is reported from recent LLM-call telemetry where available.

The admin Operations page includes a **Database records** tab. It displays paginated raw knowledge-document, chat-message, and evaluation rows, with title/content search for documents and conversation ID filters for chat/evaluation records. The existing `user_admin` permission protects both the page data and API endpoints.

## Source selection

The response includes `source_selection` with the selected source, document and analytics candidates, ranking confidence values, and a reason. The report compares freshness and evidence and notes when periods or definitions may differ. Document claims cite `[DocID:<id>]`; analytics claims cite their `[E#]` label. Scores are ranking signals, not calibrated probabilities.

## Installation

Install backend dependencies with `pip install -r requirements.txt`. OCR requires the Tesseract OCR executable on the host in addition to `pytesseract`; PDF parsing and table extraction use `pdfplumber` and `pymupdf`. Metrics are emitted directly in Prometheus text format, so no Prometheus client dependency is needed.

## Future changes

Change extraction and chunking in `app/document_processing.py`, route schemas and upload behavior in `app/document_routes.py`, and admin endpoints in `app/admin_routes.py`. Add app-state tables to `app/db.py`'s `SCHEMA`. Existing role access uses `security.require("user_admin")`.


## Persistent chat modes

`POST /api/chat` accepts the existing `message` and `conversation_id`, plus optional `document_ids` (up to 20 strings). Example: `{"message":"What were North campaign net revenue and gross margin?","conversation_id":null,"document_ids":["upload_..."]}`. With no document IDs it remains database-only. With IDs it automatically includes governed analytics evidence when available, returns a structured comparison report, and persists the exchange in normal conversation history. The assistant payload contains `source_selection` (`selected`, `candidates`, `reason`), document metadata, and citations. Chat role permission is required; the shared library is available to signed-in users.
