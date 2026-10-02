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

## 🚀 Quick Start

### 1. Deploy Container (Recommended)

To launch PytestDeck as a containerized service:

```bash
make deploy
```

*(This runs `docker compose up -d --build` in background mode)*.

Once started, open **`http://127.0.0.1:9388`** in your browser.

### 2. Local Run Mode

If you are running directly on your host machine without Docker:

```bash
make run-dev
```

Open **`http://127.0.0.1:9388`** in your browser.

---

## 🎯 How to Use PytestDeck

PytestDeck allows you to inspect and run tests across any target Python repository.

### Interactive Usage (UI)
1. Open **`http://127.0.0.1:9388`** in your browser.
2. Enter the **absolute path** of your target Python repository into the top navigation input field (e.g. `/Users/username/projects/my-python-app`).
3. Select the test suite directory (e.g. `tests/unit` or `tests/integration`).
4. Click **Refresh Tree** to scan and populate the interactive test explorer hierarchy.
5. Select individual tests or folders and click **▶ Run Selected** to execute and stream test outputs in real time.

### Default Environment Configuration (`.env`)
You can configure default target repository paths and test suite directories using a `.env` file (see `.env.example`):

```bash
# Path to target Python repository (absolute path or relative path)
TARGET_REPO=.

# Relative directory paths for test suites in target repository
UNIT_DIR=backend/tests/unit
INTEGRATION_DIR=backend/tests/integration
ACCEPTANCE_DIR=backend/tests/acceptance

PORT=9388
```

---

## 🛠️ Contributing & Development

Interested in modifying PytestDeck or contributing? Check out our [Development Guide](DEVELOPMENT.md) for repository architecture, local setup, unit/integration/E2E test commands, and linting rules.

---

## 📄 License

MIT License © 2026 PytestDeck