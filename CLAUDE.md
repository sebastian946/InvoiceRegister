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
uv run pytest test/test_llm.py::test_chain_is_built_once   # run a single test
uv run pytest -m integration         # ONLY the tests that hit Claude / Google Sheets (costs money, writes a row)
uv run pytest -m integration -k real_connection   # read-only Sheets connectivity check
uv run pytest -m integration -k real_extraction   # one real Claude call, no sheet write
```

Always use `uv run` / `uv add` rather than pip or a bare `python` so `uv.lock` stays in sync. Commit `uv.lock` alongside `pyproject.toml` changes.

Development happens on Windows with PowerShell as the primary shell, so `VAR=x uv run ...` inline env syntax does not work there; put values in `backend/.env` or use `$env:VAR = "x"; uv run ...`. No linter or formatter is configured.

## Testing

Tests live in `test/`. `pyproject.toml` sets `pythonpath = ["."]`, so tests import modules as `from utils.pdf_reader import PDFReader` and pytest must be run from `backend/`.

The unit suite is offline (no Claude, Sheets or Tesseract calls) but it is **not** credential-free. Before running it make sure:

- `ANTHROPIC_API_KEY` is set (any placeholder value works). `utils/config_env.py` instantiates `Settings()` at import time, so without it every test module fails at collection with a pydantic `Field required` error.
- `utils/invoicesheets-*.json` exists. Three tests in `test_google_sheet_connection.py` (`test_credentials_file_exists`, `test_service_account_email_is_readable`, `test_check_connection_reports_worksheet_info`) read the real file from disk even though the network is mocked.
- poppler's `pdfinfo`/`pdftoppm` is on PATH. `test_scanned_invoice_uses_ocr` mocks `pytesseract` only; `pdf2image` still rasterizes the fixture and raises `PDFInfoNotInstalledError` otherwise.

With only the API key set, expect exactly those 4 failures and 34 passes; that is the environment, not a regression.

`addopts = "-m 'not integration'"` deselects the `integration` marker by default. Any test that writes to the real Google Sheet or calls a paid API must carry `@pytest.mark.integration`; everything else mocks its external dependency:

- OCR tests patch `utils.pdf_reader.pytesseract.image_to_string` so they never need the tesseract binary.
- Google Sheets tests patch `utils.google_sheet_connection.Credentials` and `...gspread`.

Sample PDFs used as fixtures are in `test/fixtures/` and are tracked in git: `01` text-based invoice (used by the integration tests, expected number `FE-10458`), `02` scanned image invoice (OCR path), `03` an expense form that is not an invoice, and `04`–`07` generated text-based invoices (`FE-20931`, `FV-0777`, `FE-4102`, `FV-2026-0915`) meant for manual API testing so the sheet gets distinct rows. `06` carries a withholding line (retefuente) that reduces the total below subtotal plus IVA; `07` has due date equal to issue date (contado). `files_upload/` receives real uploads and is gitignored apart from its `.gitkeep`. Assertions check for text fragments rather than exact full-document output.

Route tests use `fastapi.testclient.TestClient` and monkeypatch `routes.routes.PATH_FOLDER` to a `tmp_path`, so no test writes into the repository.

## Runtime requirements

- **Environment variables** load through `utils/config_env.py` via `pydantic-settings` from `backend/.env` (gitignored). `ANTHROPIC_API_KEY` is required. `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_FILE`, `ANTHROPIC_WORKSPACE_ID`, `ALLOWED_ORIGINS` (comma-separated), `PORT`, `DEBUG`, `ENV` are optional. Import `settings` from that module rather than reading `os.environ` directly.
- **Workspace-scoped keys**: an organization-level Anthropic key rejects requests with `400 ... must include the anthropic-workspace-id header`. Either create a workspace-scoped key in the Console or set `ANTHROPIC_WORKSPACE_ID` in `.env`; `get_chain` then sends that header. A workspace-scoped key needs no header and the setting stays empty.
- **Google service account**: the key file lives in `backend/utils/` and is gitignored; name it `<anything>-service-account.json` (legacy `invoicesheets-*.json` also works) or point `GOOGLE_CREDENTIALS_FILE` at it. `find_credentials_file()` resolves it, so no project id is hard-coded. With no file present, `get_client` uses Application Default Credentials. The spreadsheet must be shared (as Editor) with the service account's `client_email`. The Google Cloud project is being migrated off `invoicesheets-509421` (its billing account was closed by Google and cannot be reopened), so never assume that project id or its `excel-editor@...` account.
- **Which Google APIs are needed**: setting `GOOGLE_SHEET_ID` in `.env` makes `open_spreadsheet` use `open_by_key`, which needs only the **Sheets API** (already enabled). Leaving it empty falls back to looking the spreadsheet up by name, which additionally needs the **Drive API** — enable it in the project or the name path returns HTTP 403. Prefer setting the id.
- **OCR needs system binaries**: `pdf2image` requires poppler (`pdfinfo`, `pdftoppm`) and `pytesseract` requires the `tesseract` binary plus the Spanish pack (`spa`), since `extract_text_from_image` defaults to `language="spa"`. Neither is a Python dependency, so `uv sync` does not install them; check with `Get-Command pdftoppm, tesseract` (PowerShell) or `command -v`. On Windows download the poppler and Tesseract builds and add their `bin` folders to PATH. Without them the scanned-PDF path (`02_factura_escaneada_imagen.pdf`) fails at runtime.

## Deployment

Target is **Google Cloud Run**, built from `backend/Dockerfile` with `gcloud run deploy --source backend` (Cloud Build builds the image; no local Docker needed). The image installs poppler and tesseract, runs `uv sync --frozen --no-dev`, and starts `python main.py`, which binds `0.0.0.0:$PORT`. `.dockerignore` / `.gcloudignore` exclude `.env`, every `*.json` and `test/`, so **no secret is ever baked into the image**: API keys come from Secret Manager via `--set-secrets`, and the service runs as the runtime service account, which `SyncGoogleSheet.get_client` picks up through `google.auth.default()` when the local key file is absent. Keep `--timeout` at 300 s or more because one extraction takes about a minute. CI lives in `.github/workflows/deploy.yml` (tests on every PR, deploy on push to `main` via Workload Identity Federation, no JSON key in GitHub).

## Architecture notes

- `utils/pdf_reader.py` — `PDFReader.read_pdf()` inspects the first page that yields content: a page with extractable text routes the whole file through `pdfplumber`; a page with only images routes it through 300 DPI rasterization plus OCR. Files matching neither return `None`. This is the ingestion entry point for the invoice pipeline.
- `utils/google_sheet_connection.py` — `SyncGoogleSheet` authorizes once in `__init__` and caches both the client and worksheet 0. Paths to the credentials file are resolved relative to the module, not the working directory, so imports work from anywhere. `add_invoice` writes to **two tabs**: worksheet 0 gets one summary row per invoice in `HEADERS` order (`Número | Emisión | Vencimiento | Proveedor | NIT | Cliente | Total`), and the `Detalle` tab gets one row per line in `DETAIL_HEADERS` order (`Número | Descripción | Cantidad | Precio unitario | Total`). The invoice number is the key joining them. Both constants must stay in sync with row 1 of their tab; changing headers in the spreadsheet without changing the constant silently writes into the wrong columns. The detail tab is created with its headers on first use, via the lazy `detail_sheet` property.
- `llm/llm.py` — extraction is a **single structured-output call**, not an agent: `PROMPT | llm.with_structured_output(Invoice, method="json_schema")`. Use `json_schema`, not the default `function_calling`, because the latter forces a tool call, which conflicts with the extended thinking that Opus 5 runs by default. The chain is built lazily behind `lru_cache` so importing the module does not need an API key. Do **not** pass `temperature`, `top_p` or `top_k`: sampling parameters were removed on this model and the API rejects them with `400 \`temperature\` is deprecated for this model`. Note that LangChain 1.x removed `AgentExecutor` and `create_tool_calling_agent`; do not reintroduce 0.x agent patterns.
- `routes/routes.py` — `POST /invoices/upload` takes a PDF, stores it under `files_upload/` (the client filename is reduced with `Path(...).name` so it cannot escape the folder), then runs the pipeline. `register=false` extracts without writing to the sheet. Errors map to 415 for a non-PDF, 422 for a PDF with no readable text, and 502 when Claude or Sheets fails. A request takes tens of seconds because extraction is synchronous.
- `utils/config_env.py` — `allowed_origins` is annotated `Annotated[list[str], NoDecode]` plus a before-validator, because pydantic-settings otherwise tries to JSON-parse list fields and rejects the comma-separated `ALLOWED_ORIGINS` value in `.env`.
- `controllers/invoice_controller.py` — the pipeline: `read_invoice` goes PDF to text to `Invoice`, and `register_invoice` also appends the rows to the sheet, accepting an injected `SyncGoogleSheet` so several invoices can share one connection.
- Module directories have no `__init__.py`; imports rely on namespace packages plus the pytest `pythonpath` setting. Directory names are lowercase (`utils`, `models`, ...) — a previous capitalized `Utils/` was renamed, so watch for stale imports and `__pycache__` leftovers.
