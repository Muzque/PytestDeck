---
name: e2e-precommit-verification
description: >-
  Mandatory pre-commit and pre-push verification workflow for PytestDeck. Use this
  skill before running git commit, git push, or opening/updating a pull request to
  ensure all code changes are verified end-to-end against sample-target-repo with
  Playwright E2E tests.
---

# 🧪 Pre-Commit & Pre-Push E2E Verification Skill

Before running `git commit`, `git push`, or opening/updating a GitHub Pull Request in PytestDeck, you **MUST** verify the changes end-to-end against `sample-target-repo` using Playwright E2E tests.

## 1. Ensure `sample-target-repo` Covers the Scenario

1. Check whether `sample-target-repo` (`tests/unit`, `tests/integration`, or `tests/acceptance`) already contains a test case that exercises the bug or feature being implemented.
2. If not, add or update a realistic test case / step / fixture in `sample-target-repo` first so the behavior is observable when running `sample-target-repo` through PytestDeck.

## 2. Add or Update a Playwright E2E Test in `frontend/e2e/app.spec.js`

1. Every user-facing feature, UI behavior, streaming parser change (`output_splitter.py`, `pytest_status_plugin.py`, `behave_formatter.py`, `useTestRunner.js`), or test execution change **must** have a corresponding Playwright E2E test in `frontend/e2e/app.spec.js` running against `sample-target-repo`.
2. Verify both targeted node selection and full-suite execution (`Run All Tests`) where applicable.

## 3. Mandatory Pre-Commit Execution Sequence

Always execute the following steps **before** `git commit` and `git push`:

```bash
# 1. Build the frontend so frontend/dist is up to date for FastAPI & Playwright
make build-frontend

# 2. Run backend & frontend linters
make lint

# 3. Run backend unit, integration, and acceptance tests
make unit-test && make integration-test && make acceptance-test

# 4. Run the targeted (or full) Playwright E2E test against sample-target-repo
cd frontend && npx playwright test e2e/app.spec.js -g "<test-name-pattern>"
```

> **Important (`reuseExistingServer`)**: If a local PytestDeck server is already running on port `9388` without `--reload` and backend code was modified, stop or restart it (`make stop`) before running Playwright so the E2E test runs against the latest backend code.

## 4. Pre-Commit & Pre-Push Gate Checklist

Do **NOT** run `git commit` or `git push` until all items below are checked:
- [ ] `sample-target-repo` has a concrete test case exercising the scenario.
- [ ] `frontend/e2e/app.spec.js` includes an E2E test verifying the behavior in the browser against `sample-target-repo`.
- [ ] `make build-frontend` and `make lint` succeeded with 0 errors.
- [ ] Playwright E2E test(s) executed and passed against `sample-target-repo`.
