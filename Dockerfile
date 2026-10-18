FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --frozen --no-dev

RUN uv build

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -m appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/dist/ ./dist/
COPY --from=builder --chown=appuser:appuser /app/.venv/ .venv/

RUN pip install --no-cache-dir --root-user-action=ignore dist/*.whl

USER appuser

EXPOSE 8000

ENTRYPOINT ["python", "-m", "fastmcp_server.server"]
