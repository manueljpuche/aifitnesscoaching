# ---------- builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml .
RUN pip install --no-cache-dir --target=/install .

# ---------- runtime ----------
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONPATH=/install

RUN groupadd -r app && useradd -r -g app -s /sbin/nologin app

COPY --from=builder /install /install

COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/

RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
