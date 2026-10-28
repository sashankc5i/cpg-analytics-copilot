# Changelog

## 2026-10-28 13:48 IST

- Added a Library tab to browse, search, preview, and attach uploaded PDFs. The paperclip menu remains upload-only.
- Persisted original PDF bytes separately from extracted text so the Library can preview the uploaded file.
- Made CPG comparison automatic whenever documents are attached. Responses use a structured report with `[DocID:...]` and `[E#]` citations, source-selection reasons, and period/definition caveats.
- Added database-only and document/report test questions to the welcome screen and README.
- Verification: frontend production build passed with the existing large-chunk advisory; Python AST/schema checks and `git diff --check` passed. Backend integration tests could not run because `pytest`, SQLAlchemy, and `httpx2` are unavailable in this environment.

## 2026-10-28 14:10 IST

- Replaced the always-visible document panel and ?Add more documents? control with a paperclip attachment menu.
- The paperclip menu now only uploads PDFs; each uploaded file is selected and shown as a compact chip above the composer.
- Updated project guides to describe the attachment workflow.
- Verification: both production build attempts transformed all 2,412 modules but Rolldown failed during rendering from system memory exhaustion; `git diff --check` passed.


## 2026-10-28 13:20 IST

- Simplified the chat composer with an ?Add more documents? control, selected-document chips, a CPG comparison toggle, and a consistent Ask button.
- Routed database-only, document-only, and comparison turns through persistent `/api/chat` so they appear in conversation history when reopened.
- Stored document citations and source-selection explanations with assistant messages; added example prompts for each mode.
- Added a four-page synthetic North Region campaign PDF with narrative, vector charts, and tables for testing extraction and citations.
- Updated project and endpoint documentation. ReportLab generated the PDF locally; no runtime dependency was added.
- Verification: frontend production build passed (with the existing chunk-size advisory), PDF page/text inspection passed, Python AST parsing passed, and `git diff --check` passed. Automated API tests could not run because this environment lacks `pytest`, `SQLAlchemy`, and `httpx2`.


## 2026-10-28 12:00 IST

- Extended the admin Database records view to include the configured analytics database (`cpg.db` locally), with discovered table/view selection, read-only paginated rows, and text search.
- Analytics table access validates names against database reflection and uses SQLAlchemy select statements; admin role checks remain required.
- Verification: admin API returned the `cpg.db` inventory (7 tables), paginated and filtered `fact_sales`, rejected an unlisted table name with 404, and denied a non-admin with 403. The prior document upload/citation and cross-user checks passed; frontend production build passed with the existing large-chunk advisory.

## 2026-10-28 11:36 IST

- Added PDF upload and a shared document library in the chat composer, with three synthetic sample PDFs for testing campaign, product quality, and supply-chain questions.
- Added cross-user document viewing, inline `[DocID:...]` reference links, source-selection details, and an extractive citation-backed fallback for local mode without Groq.
- Added an admin-only Database records tab in Operations for paginated knowledge documents, chat messages, and evaluation results, with document search and conversation filters.
- Updated document/API and project documentation. No production dependencies were added; ReportLab was installed only in the local Python environment to generate sample PDFs.
- Verification: API check confirmed PDF upload, visibility and content access across users, an offline cited answer, admin records access, and a 403 for a non-admin. PDF extraction/rendering was checked on all three files. Frontend production build passed with the existing large-chunk advisory. Temporary databases, rendered images, and build output were removed.

## 2026-10-28 10:45 IST

- Fixed the frontend login origin error by routing Vite `/api` requests to this application's backend on port 8010. Port 8000 was occupied by a different API.
- Updated local run commands and API examples to use port 8010.
- Verification: `admin` / `demo123` login through `http://localhost:5175/api/auth/login` with the browser origin returned HTTP 200 using a temporary copy of the app state database; frontend production build passed with the existing large-chunk advisory; `git diff --check` passed. Temporary database and build output were removed.

## 2026-10-28 10:21 IST

- Prefill the local login form with the seeded `admin` username and configured demo password, allowing direct sign-in. Local accounts are usernames; the screenshot email is not present as a local account.
- Fixed API error formatting so structured server errors display readable text instead of `[object Object]`.
- Verified `POST /api/auth/login` against a temporary copy of the configured state database: `admin` / `demo123` returned 200 with the admin role. All seven seeded demo password hashes matched `demo123`.
- Verification: frontend production build passed; Vite reported its bundle-size advisory. `git diff --check` passed. Temporary test data and ignored `frontend/dist` output were removed.

## 2026-10-28 10:01 IST

- Updated `frontend/src/pages/Login.jsx` so saved email/username credentials can autofill and demo-user shortcuts always submit the configured demo password.
- Verification: frontend production build passed. Vite reported the existing bundle-size advisory. The generated ignored `frontend/dist` output was removed after verification.

## 2026-10-28 01:18 IST

- Added authenticated document chat, PDF text/table extraction, optional OCR, document retrieval, and inline document citations.
- Added admin-only data browsing, evaluations, recent log streaming, constrained diagnostics, chunking inspection, and Prometheus text metrics.
- Added knowledge-document and evaluation-result tables to the app-state schema and documented endpoints in `DOCUMENT_CHAT_ADMIN.md`.
- Dependencies added: `pdfplumber`, `pymupdf`, `pytesseract`, `pillow`, and `python-multipart`.
- Verification: Python AST syntax check passed. `pytest tests/test_api.py -q` could not run because pytest is not installed; PDF/API dependency import check also found `python-multipart` missing from the current environment. No production build was run.
