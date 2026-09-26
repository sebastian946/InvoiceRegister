# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

InvoiceRegister registers invoices: a PDF is uploaded over HTTP, its text is extracted, Claude (through LangChain) turns it into a structured `Invoice`, and the result is appended to a Google Sheet. The full pipeline works end to end. The repo has two top-level folders:

- `backend/` — Python 3.12 project managed with **uv**. All current code lives here.
- `frontend/` — empty placeholder; no framework chosen yet.

The HTTP layer is FastAPI. `main.py` builds the app, adds CORS from `settings.allowed_origins` and includes the router; `routes/routes.py` holds the upload endpoint. No linter is configured yet.

The root `README.md` is the user-facing setup guide (Spanish): Google Cloud and Anthropic setup, `.env` template, curl examples and the fixture table. Keep it in sync when endpoints, env vars or sheet headers change. `backend/README.md` only points to it; `pyproject.toml` references that file, so do not delete it.

Work happens on feature branches pushed to `origin` (`setup/FolderDistribution`, `connector_gogole_xlsx`, `config_langchain`, `FeastAPi_process`, ...); `main` is the integration branch.

## Commands

All commands run from `backend/`.

```bash
uv sync                              # create .venv and install locked deps
uv run uvicorn main:app --reload     # run the API on http://127.0.0.1:8000
uv run python main.py                # same, on settings.port, reload when DEBUG

uv add <package>                     # add a dependency (updates pyproject.toml + uv.lock)
uv run pytest                        # run the unit tests
uv run pytest -v                     # one line per test
uv run pytest -k <name>              # run tests matching a name
uv run pytest -m integration         # ONLY the tests that hit Claude / Google Sheets (costs money, writes a row)
uv run pytest -m integration -k real_connection   # read-only Sheets connectivity check
uv run pytest -m integration -k real_extraction   # one real Claude call, no sheet write
```

Always use `uv run` / `uv add` rather than pip or a bare `python` so `uv.lock` stays in sync. Commit `uv.lock` alongside `pyproject.toml` changes.

## Testing

Tests live in `test/`. `pyproject.toml` sets `pythonpath = ["."]`, so tests import modules as `from utils.pdf_reader import PDFReader` and pytest must be run from `backend/`.

`addopts = "-m 'not integration'"` deselects the `integration` marker by default. Any test that writes to the real Google Sheet or calls a paid API must carry `@pytest.mark.integration`; everything else mocks its external dependency:

- OCR tests patch `utils.pdf_reader.pytesseract.image_to_string` (tesseract is not installed on this machine).
- Google Sheets tests patch `utils.google_sheet_connection.Credentials` and `...gspread`.

Sample PDFs used as fixtures are in `test/fixtures/` and are tracked in git: `01` text-based invoice (used by the integration tests, expected number `FE-10458`), `02` scanned image invoice (OCR path), `03` an expense form that is not an invoice, and `04`/`05` two generated text-based invoices (`FE-20931`, `FV-0777`) meant for manual API testing so the sheet gets distinct rows. `files_upload/` receives real uploads and is gitignored apart from its `.gitkeep`. Assertions check for text fragments rather than exact full-document output.

Route tests use `fastapi.testclient.TestClient` and monkeypatch `routes.routes.PATH_FOLDER` to a `tmp_path`, so no test writes into the repository.

## Runtime requirements

- **Environment variables** load through `utils/config_env.py` via `pydantic-settings` from `backend/.env` (gitignored). `ANTHROPIC_API_KEY` is required. `GOOGLE_SHEET_ID`, `ANTHROPIC_WORKSPACE_ID`, `ALLOWED_ORIGINS` (comma-separated), `PORT`, `DEBUG`, `ENV` are optional. Import `settings` from that module rather than reading `os.environ` directly.
- **Workspace-scoped keys**: an organization-level Anthropic key rejects requests with `400 ... must include the anthropic-workspace-id header`. Either create a workspace-scoped key in the Console or set `ANTHROPIC_WORKSPACE_ID` in `.env`; `get_chain` then sends that header. A workspace-scoped key needs no header and the setting stays empty.
- **Google service account**: `utils/invoicesheets-*.json` holds the service account private key and is gitignored. Keep it that way. The spreadsheet must be shared (as Editor) with `excel-editor@invoicesheets-509421.iam.gserviceaccount.com`.
- **Which Google APIs are needed**: setting `GOOGLE_SHEET_ID` in `.env` makes `open_spreadsheet` use `open_by_key`, which needs only the **Sheets API** (already enabled). Leaving it empty falls back to looking the spreadsheet up by name, which additionally needs the **Drive API** — currently **disabled** in project `invoicesheets-509421`, so the name path returns HTTP 403.
- **OCR needs system binaries**: `pdf2image` requires poppler (`pdftoppm`, installed) and `pytesseract` requires the `tesseract` binary plus the Spanish pack (`spa`), since `extract_text_from_image` defaults to `language="spa"`. Tesseract is **not** on PATH here, so real image-based extraction fails until it is installed.

## Architecture notes

- `utils/pdf_reader.py` — `PDFReader.read_pdf()` inspects the first page that yields content: a page with extractable text routes the whole file through `pdfplumber`; a page with only images routes it through 300 DPI rasterization plus OCR. Files matching neither return `None`. This is the ingestion entry point for the invoice pipeline.
- `utils/google_sheet_connection.py` — `SyncGoogleSheet` authorizes once in `__init__` and caches both the client and worksheet 0. Paths to the credentials file are resolved relative to the module, not the working directory, so imports work from anywhere. `add_invoice` writes to **two tabs**: worksheet 0 gets one summary row per invoice in `HEADERS` order (`Número | Emisión | Vencimiento | Proveedor | NIT | Cliente | Total`), and the `Detalle` tab gets one row per line in `DETAIL_HEADERS` order (`Número | Descripción | Cantidad | Precio unitario | Total`). The invoice number is the key joining them. Both constants must stay in sync with row 1 of their tab; changing headers in the spreadsheet without changing the constant silently writes into the wrong columns. The detail tab is created with its headers on first use, via the lazy `detail_sheet` property.
- `llm/llm.py` — extraction is a **single structured-output call**, not an agent: `PROMPT | llm.with_structured_output(Invoice, method="json_schema")`. Use `json_schema`, not the default `function_calling`, because the latter forces a tool call, which conflicts with the extended thinking that Opus 5 runs by default. The chain is built lazily behind `lru_cache` so importing the module does not need an API key. Do **not** pass `temperature`, `top_p` or `top_k`: sampling parameters were removed on this model and the API rejects them with `400 \`temperature\` is deprecated for this model`. Note that LangChain 1.x removed `AgentExecutor` and `create_tool_calling_agent`; do not reintroduce 0.x agent patterns.
- `routes/routes.py` — `POST /invoices/upload` takes a PDF, stores it under `files_upload/` (the client filename is reduced with `Path(...).name` so it cannot escape the folder), then runs the pipeline. `register=false` extracts without writing to the sheet. Errors map to 415 for a non-PDF, 422 for a PDF with no readable text, and 502 when Claude or Sheets fails. A request takes tens of seconds because extraction is synchronous.
- `utils/config_env.py` — `allowed_origins` is annotated `Annotated[list[str], NoDecode]` plus a before-validator, because pydantic-settings otherwise tries to JSON-parse list fields and rejects the comma-separated `ALLOWED_ORIGINS` value in `.env`.
- `controllers/invoice_controller.py` — the pipeline: `read_invoice` goes PDF to text to `Invoice`, and `register_invoice` also appends the rows to the sheet, accepting an injected `SyncGoogleSheet` so several invoices can share one connection.
- Module directories have no `__init__.py`; imports rely on namespace packages plus the pytest `pythonpath` setting. Directory names are lowercase (`utils`, `models`, ...) — a previous capitalized `Utils/` was renamed, so watch for stale imports and `__pycache__` leftovers.
