# ==============================================================================
# AEGIS Voice-Sentinel — production container
# Multi-stage: builds the React dashboard, then ships backend + static assets.
# ==============================================================================

# ---------- Stage 1: frontend build ----------
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: backend runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AEGIS_ENV=prod \
    AEGIS_HOST=0.0.0.0 \
    AEGIS_PORT=8000

# Runtime deps for soundfile/libgomp; create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin aegis

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /build/dist/ ./frontend/dist/

# Evidence DB location must be writable
RUN mkdir -p /app/data && chown -R aegis:aegis /app
USER aegis

ENV AEGIS_DB_SQLITE_PATH=/app/data/aegis_evidence.db

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
