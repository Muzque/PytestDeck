.PHONY: help test unit-test integration-test acceptance-test e2e-test lint build-frontend run-dev deploy

IMAGE_NAME ?= pytestdeck
IMAGE_TAG ?= latest

# Automatically load environment variables from .env if present
ENV_FILE ?= $(wildcard .env)
ifneq (,$(ENV_FILE))
    include $(ENV_FILE)
    export
endif
ENV_ARG := $(if $(ENV_FILE),--env-file $(abspath $(ENV_FILE)),)

help: ## Display available commands
	@echo "PytestDeck Automation Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: lint unit-test integration-test acceptance-test e2e-test ## Run linting, unit, integration, acceptance, and E2E tests

lint: ## Run linter and code checks
	@echo "Running Backend & Frontend Linting checks..."
	cd backend && PYTHONPATH=src:src/api uv run ruff check src tests
	cd frontend && npm run lint


unit-test: ## Run unit tests
	@echo "Running Unit Tests..."
	cd backend && PYTHONPATH=src uv run pytest tests/unit

integration-test: ## Run integration tests
	@echo "Running Integration Tests..."
	cd backend && PYTHONPATH=src uv run pytest tests/integration

acceptance-test: ## Run acceptance / BDD tests (e.g. make acceptance-test FEATURES="tests/acceptance/features/self_test.feature")
	@echo "Running Acceptance Tests..."
	cd backend && PYTHONPATH=src uv run behave $(if $(FEATURES),$(FEATURES),tests/acceptance/features)

e2e-test: ## Run frontend Playwright E2E tests
	@echo "Running Frontend E2E Tests..."
	cd frontend && npm run test:e2e

build-frontend: ## Build Vue 3 frontend SPA
	@echo "Building Frontend..."
	cd frontend && npm install && npm run build

run-dev: ## Run development server locally
	@echo "Starting PytestDeck Dev Server..."
	cd backend && PYTHONPATH=src uv run uvicorn app:app --reload --port $(or $(PORT),9388) $(ENV_ARG)

deploy: ## Build and launch Docker container in detached mode using docker compose
	@echo "Deploying PytestDeck via docker compose in detached mode..."
	docker compose up -d --build
