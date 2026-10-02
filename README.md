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

When you start PytestDeck (`make deploy` or `make run-dev`), the dashboard automatically targets `/Users/alex/projects/inventory-service` and populates the test suites matching your structure.

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