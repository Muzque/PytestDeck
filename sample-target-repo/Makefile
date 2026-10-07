.PHONY: help install sync unit-test integration-test acceptance-test test

help: ## Display available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install project dependencies with uv
	uv sync

sync: install ## Alias for install

unit-test: ## Run unit tests with uv
	@echo "Running Unit Tests..."
	PYTHONPATH=src uv run pytest tests/unit

integration-test: ## Run integration tests with uv
	@echo "Running Integration Tests..."
	PYTHONPATH=src uv run pytest tests/integration

acceptance-test: ## Run acceptance tests with uv
	@echo "Running Acceptance Tests..."
	PYTHONPATH=src uv run behave --no-capture $(if $(FEATURES),$(FEATURES),tests/acceptance/features)

test: unit-test integration-test acceptance-test ## Run all tests
