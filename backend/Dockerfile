FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONPATH=/app/src
WORKDIR /app
RUN python -m pip install --no-cache-dir uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen
COPY backend/src ./src
COPY backend/tests ./tests
RUN mkdir -p /data
ENV WELLPLAN_DB_PATH=/data/cases.sqlite3
EXPOSE 8000
CMD ["uv", "run", "--frozen", "uvicorn", "wellplan_hydraulics.api:app", "--host", "0.0.0.0", "--port", "8000"]
