# 🛠️ PytestDeck Development Guide

This guide is for developers and contributors working on the **PytestDeck** codebase.

---

## 🏗️ Repository Architecture

```text
PytestDeck/
├── backend/
│   ├── src/
│   │   ├── api/             # Modular FastAPI endpoints (health, config, discover, runner)
│   │   ├── application/     # Application use cases (DiscoverTestsUseCase)
│   │   ├── domain/          # DDD entities, models, and domain tree builder
│   │   ├── infrastructure/  # Pytest process runner & discovery integration
│   │   └── app.py           # FastAPI entry point serving SPA
│   ├── tests/
│   │   ├── unit/            # 1-to-1 unit tests mirroring src/
│   │   ├── integration/api/ # 1-to-1 API integration test modules
│   │   └── acceptance/      # Behave feature scenarios
│   └── pyproject.toml
├── frontend/                # Vue 3 SPA with xterm.js terminal integration
├── Dockerfile               # Multi-stage optimized build pipeline
├── Makefile                 # Task automation targets
├── .env.example             # Environment configuration template
└── .env                     # Local environment settings
```

---

## 💻 Local Development Setup

### Backend Development

The backend is built with FastAPI and uses `uv` for dependency management.

```bash
# Run backend dev server with auto-reload
make run

# Stop local backend dev server
make stop
```

### Frontend Development

To run the Vue 3 Vite dev server with hot module replacement (HMR):

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Automation & Testing Commands

All developer testing and build tasks are managed via `Makefile`:

```bash
# Run full test suite (lint, unit, integration, acceptance, e2e)
make test

# Run unit tests
make unit-test

# Run API integration tests
make integration-test

# Run BDD acceptance tests
make acceptance-test

# Run Playwright E2E frontend tests
make e2e-test

# Run code linting (Ruff for backend, ESLint for frontend)
make lint

# Build production frontend bundle into backend/src/frontend_dist
make build-frontend
```

---

## 🐳 Docker Build & Deployment

To test multi-stage Docker compilation locally:

```bash
make docker-run
# or
docker compose up -d --build
```
