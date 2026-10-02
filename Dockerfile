# Multi-stage Dockerfile for PytestDeck

# --- Stage 1: Python Dependency Builder ---
FROM python:3.11-slim AS python-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app/backend

# Copy project configuration and source code required for hatchling build
COPY backend/pyproject.toml backend/uv.lock* backend/README.md ./
COPY backend/src/ ./src/

# Install python dependencies into .venv
RUN uv sync --frozen

# --- Stage 2: Build Vue 3 Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 3: Final Production Runtime ---
FROM python:3.11-slim AS runner

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy pre-built virtual environment from python-builder
COPY --from=python-builder /app/backend/.venv /app/backend/.venv

# Copy backend source code and config files
COPY backend/pyproject.toml backend/uv.lock* backend/README.md ./backend/
COPY backend/src/ ./backend/src/
COPY backend/tests/ ./backend/tests/

# Copy built frontend static assets from frontend-builder
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 9388

ENV HOST=0.0.0.0
ENV PORT=9388
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH="/app/backend/src"

WORKDIR /app/backend

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9388"]
