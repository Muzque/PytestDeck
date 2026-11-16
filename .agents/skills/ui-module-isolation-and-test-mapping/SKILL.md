---
name: ui-module-isolation-and-test-mapping
description: >-
  Enforces strict subfolder isolation between PytestDeck UIs (test_deck and api_deck)
  across backend and frontend, and requires a strict 1-to-1 file mapping between
  backend/src/ source files and backend/tests/unit/ unit test files. Use this skill
  whenever adding, moving, refactoring, or reviewing backend or frontend files.
---

# 🧱 UI Module Isolation & 1-to-1 Unit Test Mapping Skill

This skill defines two mandatory structural invariants for PytestDeck so multiple developers or agents working on different UIs never touch each other's code and every backend module maintains 1-to-1 unit test coverage.

---

## 1. Subfolder Isolation per UI (`test_deck` vs `api_deck`)

Each UI mode in PytestDeck lives in its own self-contained subfolder in both `backend/src/` and `frontend/src/`.

### Backend Structure (`backend/src/`)
- **`backend/src/test_deck/`**: All Pytest / Behave Test Runner backend code (`api/`, `application/`, `domain/`, `infrastructure/`).
- **`backend/src/api_deck/`**: All API Caller & Stress Test backend code (`api/`, `domain/`, `infrastructure/`).
- **`backend/src/app.py`**: Thin FastAPI application entrypoint that only mounts routers from `test_deck` and `api_deck`.

**Backend Isolation Rules:**
1. **Zero Cross-Imports**: Code inside `backend/src/api_deck/` must **never** import from `backend/src/test_deck/`, and vice versa.
2. **Independent Persistence & Models**: Do not add API Deck tables or methods to `test_deck/infrastructure/history_db.py` or `test_deck/domain/models.py`. Keep them in `api_deck/infrastructure/api_deck_db.py` and `api_deck/domain/api_models.py`.
3. **Unique Module Basenames**: Keep module filenames distinct across subpackages (e.g., `api_routes.py`, `api_models.py`, `api_deck_db.py`) so standard `pytest` collection never encounters module name collisions.

### Frontend Structure (`frontend/src/`)
- **`frontend/src/test_deck/`**:
  - `TestDeckView.vue` (root view for the Test Runner UI)
  - `components/` (`Header.vue`, `TestExplorer.vue`, `TreeNode.vue`, `TerminalView.vue`, `MetricsSummary.vue`, `RunHistory.vue`, `TestDetailView.vue`, `RunOptionsModal.vue`, `EnvLogModal.vue`)
  - `composables/` (`useTestRunner.js`, `nodeLookup.js`, `useTheme.js`, `useTooltip.js`, `useSidebarResize.js`)
- **`frontend/src/api_deck/`**:
  - `ApiDeckView.vue` (root view for the API Caller & Stress Test UI)
  - `components/` (`ApiHeader.vue`, `ApiExplorer.vue`, `ApiTreeNode.vue`, `ApiRequestView.vue`, `ApiStressTestView.vue`, `ApiBatchSummaryView.vue`, `ApiEnvModal.vue`)
  - `composables/` (`useApiDeck.js`)
- **`frontend/src/App.vue`**: Thin `<KeepAlive>` mode switcher between `<TestDeckView />` and `<ApiDeckView />`.

**Frontend Isolation Rules:**
1. When working on a Test Runner feature/bug, only touch files under `frontend/src/test_deck/`.
2. When working on an API Deck feature/bug, only touch files under `frontend/src/api_deck/`.
3. Components and composables inside `frontend/src/api_deck/` must **never** import from `frontend/src/test_deck/`, and vice versa.

---

## 2. Strict 1-to-1 Backend Source ↔ Unit Test File Mapping

Every non-`__init__.py` Python file in `backend/src/` **MUST** have a 1-to-1 corresponding unit test file at the exact mirrored relative path under `backend/tests/unit/`:

$$\text{backend/src/}\langle\text{rel\_dir}\rangle/\langle\text{name}\rangle\text{.py} \iff \text{backend/tests/unit/}\langle\text{rel\_dir}\rangle/\text{test\_}\langle\text{name}\rangle\text{.py}$$

### Examples
| Source File (`backend/src/...`) | Required Unit Test File (`backend/tests/unit/...`) |
| --- | --- |
| `backend/src/app.py` | `backend/tests/unit/test_app.py` |
| `backend/src/api_deck/api/api_routes.py` | `backend/tests/unit/api_deck/api/test_api_routes.py` |
| `backend/src/api_deck/domain/api_models.py` | `backend/tests/unit/api_deck/domain/test_api_models.py` |
| `backend/src/api_deck/infrastructure/api_deck_db.py` | `backend/tests/unit/api_deck/infrastructure/test_api_deck_db.py` |
| `backend/src/api_deck/infrastructure/api_runner_service.py` | `backend/tests/unit/api_deck/infrastructure/test_api_runner_service.py` |
| `backend/src/test_deck/api/<module>.py` | `backend/tests/unit/test_deck/api/test_<module>.py` |
| `backend/src/test_deck/application/<module>.py` | `backend/tests/unit/test_deck/application/test_<module>.py` |
| `backend/src/test_deck/domain/<module>.py` | `backend/tests/unit/test_deck/domain/test_<module>.py` |
| `backend/src/test_deck/infrastructure/<module>.py` | `backend/tests/unit/test_deck/infrastructure/test_<module>.py` |

### Rules When Modifying Backend Files
1. **Adding a new source file**: You MUST create its 1-to-1 `test_<name>.py` counterpart in `backend/tests/unit/<rel_dir>/` first (TDD).
2. **Moving or renaming a source file**: You MUST move or rename its corresponding unit test file in `backend/tests/unit/` so the 1-to-1 mapping remains intact.
3. **Deleting a source file**: You MUST remove its corresponding unit test file in `backend/tests/unit/`.

---

## 3. Automated Verification Check

Run this check before committing any backend structural change to verify the 1-to-1 mapping between `backend/src/` and `backend/tests/unit/`:

```bash
python3 -c '
from pathlib import Path
src_root = Path("backend/src")
unit_root = Path("backend/tests/unit")
src_files = {
    p.relative_to(src_root).parent / f"test_{p.name}"
    for p in src_root.rglob("*.py")
    if p.name != "__init__.py"
}
unit_files = {
    p.relative_to(unit_root)
    for p in unit_root.rglob("test_*.py")
}
missing = sorted(src_files - unit_files)
extra = sorted(unit_files - src_files)
assert not missing and not extra, f"Missing unit tests: {missing}, Extra unit tests: {extra}"
print(f"OK: {len(src_files)} source files match 1-to-1 with {len(unit_files)} unit test files.")
'
```
