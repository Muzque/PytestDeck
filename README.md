# ⚡ PytestDeck

Lightweight cross-project Python test control deck built with FastAPI, Vue 3 SPA, and Domain-Driven Design (DDD).

![PytestDeck Dashboard](frontend/src/assets/hero.png)

---

## 🌟 Overview

**PytestDeck** provides a modern, interactive web control dashboard for discovering and streaming execution logs for Python test suites (`pytest` and `behave`).

- ⚡ **Lightweight DDD Architecture**: Clean domain models, use cases, and modular FastAPI routers (`backend/src/`).
- 🌲 **Interactive Test Explorer**: Hierarchical discovery tree (directories, files, classes, and test functions).
- 💻 **Real-Time xterm.js Terminal**: Live ANSI color test output streamed over WebSockets.
- 🐳 **Multi-Stage Docker Setup**: High-efficiency build cache separating frontend compilation, `uv` dependency syncing, and execution layers.

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
└── pytestdeck.toml          # Target repository suite configuration
```

---

## 🚀 Quick Start

### 1. Local Development Mode

Start the FastAPI dev server (with built SPA assets):

```bash
make run-dev
```
Open **`http://127.0.0.1:9388`** in your browser.

### 2. Frontend Development

To run the Vue 3 Vite dev server with hot module replacement:

```bash
cd frontend
npm run dev
```

---

## 🎯 Tutorial: Changing Target Repositories

PytestDeck allows you to inspect and run tests across any target Python repository.

### Option A: From the UI (Interactive)
1. Open **`http://127.0.0.1:9388`** in your browser.
2. Enter the **absolute path** of your target Python repository into the top navigation input field (e.g. `/Users/username/projects/my-python-app`).
3. Select the test suite directory (e.g. `tests/unit` or `tests/integration`).
4. Click **Refresh Tree** to scan and populate the interactive test explorer hierarchy.

### Option B: Pre-configuring `pytestdeck.toml`
Create or update `pytestdeck.toml` at the target repo root to define suite structures:

```toml
[pytestdeck]
unit_dir = "tests/unit"
integration_dir = "tests/integration"

[pytestdeck.suites.unit]
runner = "pytest"
ini_file = "tests/unit/pytest.ini"

[pytestdeck.suites.integration]
runner = "pytest"
ini_file = "tests/integration/pytest.ini"
```

---

## 🧪 Running Automation Commands

All primary automation commands are managed via `Makefile`:

```bash
# Run unit tests
make unit-test

# Run API integration tests
make integration-test

# Run BDD acceptance tests
make acceptance-test

# Run lint checks
make lint

# Build production frontend bundle
make build-frontend

# Build Docker container image
make deploy
```

---

## 🐳 Docker Deployment

Build the container image using multi-stage cached layers:

```bash
make deploy
```

Run the containerized server on port `9388`:

```bash
docker run -p 9388:9388 pytestdeck:latest
```

---

## 📄 License

MIT License © 2026 PytestDeck