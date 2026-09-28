# One image for the whole app. Build context is the repository root.
# Stage 1 builds the React frontend, stage 2 runs FastAPI and serves it.

# ---- Stage 1: frontend build -------------------------------------------------
FROM node:24-slim AS frontend

WORKDIR /frontend

# Install locked dependencies first so this layer is cached across code changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: runtime --------------------------------------------------------
FROM python:3.12-slim

# System binaries that uv cannot install: poppler for pdf2image, tesseract for OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ .

# main.py serves this folder at "/". Node itself is not part of the final image.
COPY --from=frontend /frontend/dist ./static

# Run as an unprivileged user. /app must stay writable for files_upload/.
RUN useradd --create-home app && chown -R app:app /app
USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# main.py binds 0.0.0.0 on $PORT, which Cloud Run injects.
CMD ["python", "main.py"]
