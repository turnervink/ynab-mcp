FROM python:3.12-slim-bookworm AS builder
ENV POETRY_VERSION=2.5.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry-cache \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=/tmp/poetry-cache poetry install --only main --no-root
COPY README.md ./
COPY src ./src
RUN poetry install --only main

FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 1000 app && mkdir /data && chown app:app /data
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FASTMCP_HOME=/data/fastmcp
USER app
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
CMD ["python", "-m", "ynab_mcp"]
