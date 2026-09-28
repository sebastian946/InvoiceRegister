# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

InvoiceRegister registers invoices: a PDF is uploaded over HTTP, its text is extracted, Claude (through LangChain) turns it into a structured `Invoice`, and the result is appended to a Google Sheet. The full pipeline works end to end. The repo has two top-level folders:

- `backend/` — Python 3.12 project managed with **uv**. API, pipeline and tests.
- `frontend/` — React 19 + TypeScript + Vite + Tailwind CSS 4 single-page app (upload form, extracted invoice view, per-session history). Managed with **npm**.

The HTTP layer is FastAPI. `main.py` builds the app, adds CORS from `settings.allowed_origins`, includes the router and, last, mounts the built frontend at `/`; `routes/routes.py` holds the upload endpoint. The backend has no linter; the frontend uses oxlint.

**Frontend and backend ship as one service on one origin.** In production FastAPI serves the built frontend, so the browser calls the API with relative paths (`/invoices/upload`, `/Health`) and CORS is not involved. In development Vite proxies those same paths to the backend. Never hard-code an API host in the frontend.

The root `README.md` is the user-facing setup guide (Spanish): Google Cloud and Anthropic setup, `.env` template, curl examples and the fixture table. Keep it in sync when endpoints, env vars or sheet headers change. `backend/README.md` only points to it; `pyproject.toml` references that file, so do not delete it.

Work happens on feature branches pushed to `origin` (`setup/FolderDistribution`, `connector_gogole_xlsx`, `config_langchain`, `FeastAPi_process`, ...); `main` is the integration branch.

## Commands

Frontend commands run from `frontend/`:

```bash
npm install                          # install locked deps
npm run dev                          # http://localhost:5173, proxies the API to http://127.0.0.1:8000
npm run build                        # type-check (tsc -b) and build into frontend/dist
npm run lint                         # oxlint
```

Use `localhost`, not `127.0.0.1`, for the Vite dev server: on this machine it listens on IPv6 only. Which backend the frontend uses is set by env files in `frontend/`, never in code. `.env.development` (committed) sets `BACKEND_URL=http://127.0.0.1:8000`, the dev proxy target. `.env.production` (committed) sets `VITE_API_BASE` empty, meaning same origin, which is correct because one Cloud Run service serves page and API. To point a local frontend at the deployed backend, copy `.env.example` to `.env.local` (gitignored) and fill `BACKEND_URL` plus `BACKEND_TOKEN` (from `gcloud auth print-identity-token`, valid one hour); the Vite proxy adds it as a Bearer header. Real environment variables override the files. `BACKEND_*` names deliberately lack the `VITE_` prefix, which would bake them into browser code, so never put a token in a `VITE_` variable. The token route stops working once IAP is enabled on the service. The root `.gitignore`, `.dockerignore` and `.gcloudignore` ignore `.env.*` but carry explicit exceptions for these committed files.

Google credentials expire: the `dzlabs.co` Workspace forces periodic reauthentication. When uploads fail locally with `RefreshError: Reauthentication is needed` (surfaced by the API as 502), run `gcloud auth login` and then `gcloud auth application-default login --impersonate-service-account=sheet-editor@dzlabs-invoice-register.iam.gserviceaccount.com`. After `npm run build`, the backend alone serves the whole app at `http://127.0.0.1:8000/`.

Backend commands run from `backend/`.

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
- poppler's `pdfinfo`/`pdftoppm` is on PATH. `test_scanned_invoice_uses_ocr` mocks `pytesseract` only; `pdf2image` still rasterizes the fixture and raises `PDFInfoNotInstalledError` otherwise.

No service account key is needed: the sheet tests write a fake key into `tmp_path`, and the one test that reads a real key is skipped when none is present. Without poppler, expect exactly that 1 failure; it is the environment, not a regression.

The frontend has no unit tests. `npm run build` is its check, since it type-checks before bundling. `test/test_frontend.py` covers how the backend serves the built files and that API routes take precedence over the static mount.

`addopts = "-m 'not integration'"` deselects the `integration` marker by default. Any test that writes to the real Google Sheet or calls a paid API must carry `@pytest.mark.integration`; everything else mocks its external dependency:

- OCR tests patch `utils.pdf_reader.pytesseract.image_to_string` so they never need the tesseract binary.
- Google Sheets tests patch `utils.google_sheet_connection.Credentials` and `...gspread`.

Sample PDFs used as fixtures are in `test/fixtures/` and are tracked in git: `01` text-based invoice (used by the integration tests, expected number `FE-10458`), `02` scanned image invoice (OCR path), `03` an expense form that is not an invoice, and `04`–`07` generated text-based invoices (`FE-20931`, `FV-0777`, `FE-4102`, `FV-2026-0915`) meant for manual API testing so the sheet gets distinct rows. `06` carries a withholding line (retefuente) that reduces the total below subtotal plus IVA; `07` has due date equal to issue date (contado). `files_upload/` receives real uploads and is gitignored apart from its `.gitkeep`. Assertions check for text fragments rather than exact full-document output.

Route tests use `fastapi.testclient.TestClient` and monkeypatch `routes.routes.PATH_FOLDER` to a `tmp_path`, so no test writes into the repository.

## Runtime requirements

- **Environment variables** load through `utils/config_env.py` via `pydantic-settings` from `backend/.env` (gitignored). `ANTHROPIC_API_KEY` is required. `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_FILE`, `FRONTEND_DIR`, `ANTHROPIC_WORKSPACE_ID`, `ALLOWED_ORIGINS` (comma-separated), `PORT`, `DEBUG`, `ENV` are optional. Import `settings` from that module rather than reading `os.environ` directly.
- **Workspace-scoped keys**: an organization-level Anthropic key rejects requests with `400 ... must include the anthropic-workspace-id header`. Either create a workspace-scoped key in the Console or set `ANTHROPIC_WORKSPACE_ID` in `.env`; `get_chain` then sends that header. A workspace-scoped key needs no header and the setting stays empty.
- **Google service account**: the key file lives in `backend/utils/` and is gitignored; name it `<anything>-service-account.json` (legacy `invoicesheets-*.json` also works) or point `GOOGLE_CREDENTIALS_FILE` at it. `find_credentials_file()` resolves it, so no project id is hard-coded. With no file present, `get_client` uses Application Default Credentials. The spreadsheet must be shared (as Editor) with the service account's `client_email`. The Google Cloud project is being migrated off `invoicesheets-509421` (its billing account was closed by Google and cannot be reopened), so never assume that project id or its `excel-editor@...` account.
- **Which Google APIs are needed**: setting `GOOGLE_SHEET_ID` in `.env` makes `open_spreadsheet` use `open_by_key`, which needs only the **Sheets API** (already enabled). Leaving it empty falls back to looking the spreadsheet up by name, which additionally needs the **Drive API** — enable it in the project or the name path returns HTTP 403. Prefer setting the id.
- **OCR needs system binaries**: `pdf2image` requires poppler (`pdfinfo`, `pdftoppm`) and `pytesseract` requires the `tesseract` binary plus the Spanish pack (`spa`), since `extract_text_from_image` defaults to `language="spa"`. Neither is a Python dependency, so `uv sync` does not install them; check with `Get-Command pdftoppm, tesseract` (PowerShell) or `command -v`. On Windows download the poppler and Tesseract builds and add their `bin` folders to PATH. Without them the scanned-PDF path (`02_factura_escaneada_imagen.pdf`) fails at runtime.

## Deployment

Target is **Google Cloud Run**, one service named `invoice-register` in project `dzlabs-invoice-register`, region `us-central1`. It is built from the **root** `Dockerfile` with `gcloud run deploy invoice-register --source . --region us-central1` run from the repository root (Cloud Build builds the image; no local Docker needed). The Dockerfile is multi-stage: a Node stage runs `npm ci && npm run build`, then the Python stage installs poppler and tesseract, runs `uv sync --frozen --no-dev`, copies `backend/` plus the built frontend into `/app/static`, and starts `python main.py`, which binds `0.0.0.0:$PORT`.

Root `.dockerignore` and `.gcloudignore` keep `.env` and service account keys out, so **no secret is ever baked into the image**: API keys come from Secret Manager via `--set-secrets`, and the service runs as `sheet-editor@dzlabs-invoice-register.iam.gserviceaccount.com`, which `SyncGoogleSheet.get_client` picks up through `google.auth.default()`. Two traps: `.gcloudignore` must not exclude `Dockerfile` (the build fails with `lstat /workspace/Dockerfile`), and neither ignore file may exclude `*.json`, because the frontend build needs `package.json`, `package-lock.json` and the tsconfig files.

The `dzlabs.co` organization enforces two policies that shape the setup: service account keys cannot be created (local development uses `gcloud auth application-default login --impersonate-service-account=...`), and `allUsers` bindings are rejected, so the service cannot be made public with `--allow-unauthenticated`. Browser access goes through Identity-Aware Proxy restricted to the domain. Keep `--timeout` at 300 s or more because one extraction can take close to a minute, and keep `LANGCHAIN_CALLBACKS_BACKGROUND=false` so traces are flushed before Cloud Run throttles the CPU. There is no CI workflow yet; deploys are manual.

## Architecture notes

- `frontend/src/` — `api.ts` is the only module that talks to the backend: it owns the response types (keep them in sync with `backend/models/models.py`), client-side file validation, a 240 s timeout and the mapping from HTTP status to a Spanish message. `App.tsx` holds all state; `components/` are presentational. Invoice values come from a model reading an untrusted PDF, so render them as React text only and never through `dangerouslySetInnerHTML`. The history list is in-memory and is lost on reload by design; the sheet is the permanent record.
- `main.py` static mount — `mount_frontend` must be the last registration, because a mount at `/` swallows every path no earlier route matched. `find_frontend_dir` looks at `FRONTEND_DIR`, then `backend/static` (image), then `frontend/dist` (local build). With no build present the API runs alone and `/` returns 404.

- `utils/pdf_reader.py` — `PDFReader.read_pdf()` inspects the first page that yields content: a page with extractable text routes the whole file through `pdfplumber`; a page with only images routes it through 300 DPI rasterization plus OCR. Files matching neither return `None`. This is the ingestion entry point for the invoice pipeline.
- `utils/google_sheet_connection.py` — `SyncGoogleSheet` authorizes once in `__init__` and caches both the client and worksheet 0. Paths to the credentials file are resolved relative to the module, not the working directory, so imports work from anywhere. `add_invoice` writes to **two tabs**: worksheet 0 gets one summary row per invoice in `HEADERS` order (`Número | Emisión | Vencimiento | Proveedor | NIT | Cliente | Total`), and the `Detalle` tab gets one row per line in `DETAIL_HEADERS` order (`Número | Descripción | Cantidad | Precio unitario | Total`). The invoice number is the key joining them. Both constants must stay in sync with row 1 of their tab; changing headers in the spreadsheet without changing the constant silently writes into the wrong columns. The detail tab is created with its headers on first use, via the lazy `detail_sheet` property.
- `llm/llm.py` — extraction is a **single structured-output call**, not an agent: `PROMPT | llm.with_structured_output(Invoice, method="json_schema")`. Use `json_schema`, not the default `function_calling`, because the latter forces a tool call, which conflicts with the extended thinking that Opus 5 runs by default. The chain is built lazily behind `lru_cache` so importing the module does not need an API key. Do **not** pass `temperature`, `top_p` or `top_k`: sampling parameters were removed on this model and the API rejects them with `400 \`temperature\` is deprecated for this model`. Note that LangChain 1.x removed `AgentExecutor` and `create_tool_calling_agent`; do not reintroduce 0.x agent patterns.
- `routes/routes.py` — `POST /invoices/upload` takes a PDF, stores it under `files_upload/` (the client filename is reduced with `Path(...).name` so it cannot escape the folder), then runs the pipeline. `register=false` extracts without writing to the sheet. Errors map to 415 for a non-PDF, 422 for a PDF with no readable text, and 502 when Claude or Sheets fails. A request takes tens of seconds because extraction is synchronous.
- `utils/config_env.py` — `allowed_origins` is annotated `Annotated[list[str], NoDecode]` plus a before-validator, because pydantic-settings otherwise tries to JSON-parse list fields and rejects the comma-separated `ALLOWED_ORIGINS` value in `.env`.
- `controllers/invoice_controller.py` — the pipeline: `read_invoice` goes PDF to text to `Invoice`, and `register_invoice` also appends the rows to the sheet, accepting an injected `SyncGoogleSheet` so several invoices can share one connection.
- Module directories have no `__init__.py`; imports rely on namespace packages plus the pytest `pythonpath` setting. Directory names are lowercase (`utils`, `models`, ...) — a previous capitalized `Utils/` was renamed, so watch for stale imports and `__pycache__` leftovers.
