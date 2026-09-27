.PHONY: help unit-test integration-test acceptance-test lint build-frontend run-dev deploy

IMAGE_NAME ?= pytestdeck
IMAGE_TAG ?= latest

help: ## Display available commands
	@echo "PytestDeck Automation Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

lint: ## Run linter and code checks
	@echo "Running Linting & Formatting checks..."
	cd backend && PYTHONPATH=src:src/api uv run ruff check src tests || true

unit-test: ## Run unit tests
	@echo "Running Unit Tests..."
	cd backend && PYTHONPATH=src uv run pytest tests/unit

integration-test: ## Run integration tests
	@echo "Running Integration Tests..."
	cd backend && PYTHONPATH=src uv run pytest tests/integration

acceptance-test: ## Run acceptance / BDD tests
	@echo "Running Acceptance Tests..."
	cd backend && PYTHONPATH=src uv run behave tests/acceptance/features

build-frontend: ## Build Vue 3 frontend SPA
	@echo "Building Frontend..."
	cd frontend && npm install && npm run build

run-dev: ## Run development server locally
	@echo "Starting PytestDeck Dev Server..."
	cd backend && PYTHONPATH=src uv run uvicorn app:app --reload --port 8000

deploy: ## Build Docker container for deployment
	@echo "Building Docker container for deployment..."
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
