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

### 1. Local Run Mode (Recommended — Save Time on `uv sync`)

Running PytestDeck directly on your host machine is the **recommended mode**:

```bash
make run
```

Open **`http://127.0.0.1:9388`** in your browser.

> [!TIP]
> **Why `make run` is recommended over Docker**:
> - **Zero `uv sync` wait time**: `make run` reuses your target repository's existing local `.venv` virtual environment directly. It skips building a separate Linux virtual environment, eliminating download and compilation delays.
> - **Instant startup**: Auto-loads `.env` (including `TARGET_REPO`, suite paths, and `PORT`) with automatic frontend compilation and backend hot-reloading.
>
> Simply ensure your target repository's local environment is synced beforehand:
> ```bash
> cd /path/to/target-repo && uv sync --all-groups
> ```
> *(`pytest-json-report`, which PytestDeck needs for discovery and reports, is injected dynamically via `uv run --with`; no changes to the target's dependencies are required.)*

To stop the locally running server at any time:

```bash
make stop
```

---

### 2. Docker Container Mode

If you prefer to launch PytestDeck as an isolated containerized service:

```bash
make docker-run
```

*(This runs `docker compose up -d --build` in background mode)*.

Once started, open **`http://127.0.0.1:9388`** in your browser.

> **How target dependencies work in Docker**
>
> Tests always run with the **target repository's own `uv` project** (its `pyproject.toml` / `uv.lock`), not PytestDeck's packages.
> Because the host's `.venv` is built for macOS/Windows and can't run inside a Linux container, the container builds a separate Linux environment on startup:
>
> - `uv sync --all-groups` runs **in the background**, so the UI is available immediately.
> - **In the UI**: The **Terminal Output** tab streams the live package preparation progress automatically. You can also click the status badge (`Preparing Env...` / `Ready` / `Env Failed`) in the top navigation header at any time to open the **Environment Setup Logs** modal.
> - **In the Terminal**: Follow progress with `docker logs -f pytestdeck`, or `docker exec pytestdeck cat /cache/env_sync.log`.
> - The environment, uv cache and Python installs are stored in the `pytestdeck_cache` Docker volume. The **first** start downloads everything; later deploys only re-sync when `uv.lock` changes.
> - To reset it (e.g. after switching `TARGET_REPO`): `docker compose down -v`.

---

## 🎯 How to Use PytestDeck

PytestDeck allows you to inspect and run tests across any target Python repository.

### Interactive Usage (UI)
1. Open **`http://127.0.0.1:9388`** in your browser.
2. Enter the **absolute path** of your target Python repository into the top navigation input field (e.g. `/Users/username/projects/my-python-app`).
3. Select the test suite directory (e.g. `tests/unit` or `tests/integration`).
4. Click **Refresh Tree** to scan and populate the interactive test explorer hierarchy.
5. Select individual tests or folders and click **▶ Run Selected** to execute and stream test outputs in real time.

---

## ⚙️ Environment Configuration (`.env`)

You can set default target repository paths and test suite directories using a `.env` file created at the PytestDeck root (copied from `.env.example`).

### Sample Case Scenario

Suppose you have a target project located on your system at `/Users/alex/projects/inventory-service`, with tests organized in `tests/unit`, `tests/integration`, and `tests/acceptance`.

Create a `.env` file with the following configuration:

```env
# Absolute path to the target Python repository
TARGET_REPO=/Users/alex/projects/inventory-service

# Relative paths to test suite directories inside the target repository
UNIT_DIR=tests/unit
INTEGRATION_DIR=tests/integration
ACCEPTANCE_DIR=tests/acceptance

# PytestDeck web port
PORT=9388
```

### Target Repository Directory Structure

For the `.env` settings above, your target Python repository layout looks like this:

```text
inventory-service/                    # TARGET_REPO=/Users/alex/projects/inventory-service
├── src/                              # Application source code
│   └── inventory/
│       ├── __init__.py
│       └── service.py
├── tests/
│   ├── unit/                         # UNIT_DIR=tests/unit
│   │   ├── pytest.ini                # Suite-level pytest configuration
│   │   └── test_service.py           # Unit test module
│   ├── integration/                  # INTEGRATION_DIR=tests/integration
│   │   ├── pytest.ini                # Suite-level pytest configuration
│   │   └── test_api.py               # Integration test module
│   └── acceptance/                   # ACCEPTANCE_DIR=tests/acceptance
│       └── features/                 # Behave BDD feature files
│           └── inventory.feature
├── pytest.ini                        # Optional repository root pytest configuration
└── pyproject.toml
```

When you start PytestDeck (`make run` or `make docker-run`), the dashboard automatically targets `/Users/alex/projects/inventory-service` and populates the test suites matching your structure.

---

## ⚙️ Target Repository `pytest.ini` Support

PytestDeck seamlessly integrates with your target repository's standard `pytest.ini` (as well as `pyproject.toml` or `setup.cfg`).

When PytestDeck discovers and executes tests, it automatically inherits and applies the arguments, markers, and path settings defined in your target repo's `pytest.ini`.

### Sample `pytest.ini`

Place a `pytest.ini` file at the root or test directory of your target repository:

```ini
[pytest]
# Minimum pytest version requirement
minversion = 7.0

# Add default command-line options
addopts = -v --tb=short --strict-markers

# Register custom test markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests requiring external services
    smoke: core sanity checks

# Custom test file naming patterns
python_files = test_*.py *_test.py
python_classes = Test* *Suite
python_functions = test_*

# Add source directory to pythonpath
pythonpath = src
```

PytestDeck automatically respects these options during execution—including custom markers passed via the UI filter bar and module import paths.

---

## 🛠️ Contributing & Development

Interested in modifying PytestDeck or contributing? Check out our [Development Guide](DEVELOPMENT.md) for repository architecture, local setup, unit/integration/E2E test commands, and linting rules.

---

## 📄 License

MIT License © 2026 PytestDeck