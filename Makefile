.PHONY: help install lint format typecheck test clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

lint: ## Run ruff linter
	uv run ruff check custom_components/

format: ## Format code with ruff
	uv run ruff format custom_components/
	uv run ruff check --fix custom_components/

typecheck: ## Run mypy type checker
	uv run mypy custom_components/groq/

test: ## Run tests
	uv run pytest

clean: ## Clean build artifacts and caches
	rm -rf .venv/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: install lint typecheck ## Install and run all checks
