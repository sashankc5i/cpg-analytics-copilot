# Project documentation

## Overview

CPG Analytics Copilot is a React/Vite client backed by FastAPI. Existing `/api/*` features provide authentication, governed analytics chat, investigations, governance, and telemetry. New document chat answers from stored or uploaded PDFs with citations. New admin APIs inspect state data, review evaluation metrics, inspect logs, clear analytics caches, and view request metrics.

## Structure and important files

- `backend/app/main.py`: FastAPI app, startup lifecycle, middleware, request IDs, router registration, static frontend serving, and `/metrics`.
- `backend/app/routes.py`: existing `/api/*` endpoints; leave unrelated routes here unchanged.
- `backend/app/document_routes.py`: authenticated document chat and PDF upload endpoints.
- `backend/app/document_processing.py`: PDF extraction, OCR fallback, text chunking, document lookup/search, source ranking, and LLM prompt/citations.
- `backend/app/admin_routes.py`: admin-only browsing, evaluations, log streaming, diagnostics, and chunking inspection.
- `backend/app/evaluation.py`: recent-message evaluation heuristic and summary queries.
- `backend/app/security.py`: JWT/OIDC identity, role mapping, and feature-based RBAC.
- `backend/app/db.py`: SQLite state schema and analytics database access. State tables are initialized by `db.init_state()` during app lifespan.
- `backend/app/llm.py`: configured Groq client wrapper and telemetry.
- `backend/app/logging_setup.py`: structured logs, request correlation, and bounded in-memory recent log buffer.
- `backend/app/analytics/`: governed CPG query and calculation logic.
- `backend/requirements.txt`: backend dependencies.
- `frontend/`: React/Vite client.
- `frontend/src/pages/Login.jsx`: sign-in page, browser credential autofill fields, default local `admin` demo credentials, and demo-user shortcuts. `frontend/src/auth.jsx` stores the session and calls the existing login API; `frontend/src/api.js` converts server errors to readable messages.

## Document storage and chat

`knowledge_documents` stores `id`, `title`, extracted `content`, `source`, `updated_at`, and JSON metadata. `knowledge_document_files` stores original uploaded PDF bytes for in-browser preview from the **Library** tab. Search matches document title/content. Any signed-in user can browse uploaded PDFs, preview the original, and attach a saved document to chat. The paperclip menu uploads a new PDF; uploaded files appear as attachment chips. With document IDs, `POST /api/chat` automatically includes governed CPG evidence when available and returns a structured comparison report with source evidence and `source_selection`. Every turn is persisted. Local mode without Groq produces a source comparison report with extractive citations.

Text and tables are extracted page by page; image-only pages are OCR'd when Tesseract is installed. `chunk_text` provides overlapping character chunks for inspection. Four fictional sample PDFs in `frontend/public/sample-documents/` are available for manual upload tests, including a four-page report with vector charts and tables. Edit mode prompts in `frontend/src/pages/Chat.jsx`; update extraction, source selection, or citations in `backend/app/document_processing.py`.

LLM answers are constrained to supplied context and instructed to cite document claims as `[DocID:<id>]` and CPG claims as `[E#]`. `source_selection` compares freshness and evidence quality; ranking confidence is not calibrated probability. Reports note when periods or metric definitions may not be comparable. Add extraction and ranking rules in `document_processing.py`.

## Admin and evaluation behavior

Every `/admin/*` endpoint and `/metrics` depends on `security.require("user_admin")`; in current role configuration only admin has this feature. The Operations page's **Database records** tab shows paginated app-state records and the configured analytics database (`cpg.db` locally). Analytics table/view names come from database reflection; row reads are select-only, paginated, and support text search. Admin table names are allow-listed and pagination parameters are bounded. The diagnostics API accepts exactly `health` and `cache_clear`; it never executes arbitrary shell input.

Evaluation results are stored in `evaluation_results`. Accuracy is a transparent citation/evidence grounding heuristic, not verified factual accuracy. Citation correctness checks cited evidence labels against the message payload. Latency uses LLM telemetry where available. Review or replace these scoring rules in `evaluation.py` before treating them as production quality scores.

## Configuration and installation

Use the existing `.env` settings (`GROQ_API_KEY`, `GROQ_MODEL`, `AUTH_MODE`, JWT/OIDC values, and database URLs). Install dependencies with `pip install -r backend/requirements.txt`. PDF text and tables use `pdfplumber`/`pymupdf`; OCR requires the Tesseract executable plus `pytesseract` and Pillow. Prometheus metrics use the text exposition format directly and do not require `prometheus-client`.

## Run, test, and deploy

From `backend/`, install requirements and run `uvicorn app.main:app --reload --host 127.0.0.1 --port 8010`. Existing tests run with `pytest tests`. Before deployment, set a unique `JWT_SECRET`, configure OIDC where appropriate, set CORS origins and LLM/database environment values, and install Tesseract if OCR is required. The `knowledge_document_files` state table is created automatically by the existing `db.init_state()` startup call; no destructive migration is used. Keep `/metrics` behind the existing admin authentication when configuring a scraper.

## API reference

See [`backend/DOCUMENT_CHAT_ADMIN.md`](backend/DOCUMENT_CHAT_ADMIN.md) for methods, payloads, response examples, permissions, and conflict-selection details for every new endpoint.

## Common modifications

- Change chunk size/overlap defaults in `document_processing.py`.
- Change upload limit and file extraction in `document_processing.py` and `document_routes.py`.
- Change admin filters or add a data view in `admin_routes.py`, maintaining an explicit table allow-list.
- Change evaluation scoring in `evaluation.py` and document its limitations.
- Add state tables in `db.py`'s `SCHEMA`; the existing startup initializer creates them.

## Known limitations

- Existing app state is SQLite; document content is stored in full and does not yet use vector embeddings or semantic ranking.
- OCR depends on a host-installed Tesseract executable and can be skipped when unavailable.
- Evaluation values are heuristic proxies and need human review for quality decisions.
- `/metrics` is an in-process counter and resets when the process restarts; use one process or aggregate at the deployment layer.
