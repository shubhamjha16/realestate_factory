# Real Estate Factory — engine.
#
# One image serves both Render services: the web process and the arq worker
# (S4). They differ only in start command, so they cannot drift apart in
# dependencies — a worker running different library versions from the API is a
# class of bug that is very hard to see.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# libreoffice converts DOCX to PDF; tesseract with Hindi reads scanned title
# deeds and approvals (S6). Both are runtime dependencies of the document path,
# not conveniences.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-hin \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies resolve from the lockfile in their own layer, so a source change
# does not reinstall LibreOffice's Python bindings on every build.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Never run as root: the OCR path parses attacker-supplied PDFs (S20).
RUN useradd --create-home --uid 10001 factory \
    && chown -R factory:factory /app
USER factory

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8004/api/v1/health || exit 1

# Migrations run as Render's pre-deploy command, never in this process — §9.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
