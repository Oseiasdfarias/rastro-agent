FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project --extra dev
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --extra dev

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 app
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app pyproject.toml README.md ./
COPY --chown=app src ./src
COPY --chown=app tests ./tests
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 HF_HOME=/app/.cache/hf
RUN mkdir -p /app/data /app/results /app/.cache/hf && chown app /app && chown -R app /app/data /app/results /app/.cache
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "rootcause.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
