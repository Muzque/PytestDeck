.PHONY: help test unit-test integration-test acceptance-test e2e-test lint build-frontend run dev stop docker-run

IMAGE_NAME ?= pytestdeck
IMAGE_TAG  ?= latest

# Automatically load environment variables from .env if present
ENV_FILE ?= $(wildcard .env)
ifneq (,$(ENV_FILE))
    include $(ENV_FILE)
    export
endif
ENV_ARG := $(if $(ENV_FILE),--env-file $(abspath $(ENV_FILE)),)

help: ## Display available commands
	@echo "PytestDeck Automation Commands:"
	@awk 'BEGIN {FS = ":.*## "} /^##@/ { printf "\n\033[1m%s:\033[0m\n", substr($$0, 5) } /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

##@ Testing
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

##@ Deployment
build-frontend: ## Build Vue 3 frontend SPA
	@echo "Building Frontend..."
	cd frontend && npm install && npm run build

run: build-frontend ## Run PytestDeck server locally
	@echo "Starting PytestDeck Server..."
	cd backend && PYTHONPATH=src uv run uvicorn app:app --port $(or $(PORT),9388) $(ENV_ARG) $(if $(RELOAD),--reload,)

dev: build-frontend ## Run PytestDeck in development mode with auto-reload
	@echo "Starting PytestDeck Dev Server with auto-reload..."
	cd backend && PYTHONPATH=src uv run uvicorn app:app --reload --port $(or $(PORT),9388) $(ENV_ARG)

stop: ## Stop the locally running PytestDeck dev server (macOS and Linux)
	@echo "Stopping PytestDeck Dev Server on port $(or $(PORT),9388)..."
	@PORT_NUM=$(or $(PORT),9388); \
	PIDS=$$(lsof -ti tcp:$$PORT_NUM 2>/dev/null || fuser $$PORT_NUM/tcp 2>/dev/null || pgrep -f "uvicorn app:app.*$$PORT_NUM" 2>/dev/null); \
	if [ -n "$$PIDS" ]; then \
		echo "Stopping process(es): $$PIDS"; \
		kill $$PIDS 2>/dev/null || true; \
		sleep 0.5; \
		REMAINING=$$(lsof -ti tcp:$$PORT_NUM 2>/dev/null || fuser $$PORT_NUM/tcp 2>/dev/null); \
		if [ -n "$$REMAINING" ]; then \
			kill -9 $$REMAINING 2>/dev/null || true; \
		fi; \
		echo "PytestDeck stopped."; \
	else \
		echo "No PytestDeck server running on port $$PORT_NUM."; \
	fi

docker-run: ## Build and launch Docker container in detached mode using docker compose
	@echo "Deploying PytestDeck via docker compose in detached mode..."
	docker compose up -d --build
