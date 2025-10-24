SHELL := /bin/bash

# =============================================================================
# Configuration and Environment Variables
# =============================================================================

.DEFAULT_GOAL := help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# ----------------------------------------------------------------------------
# Display Formatting and Colors
# ----------------------------------------------------------------------------
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")
ERROR := $(shell printf "$(RED)✖$(NC)")

# =============================================================================
# Help and Documentation
# =============================================================================
.PHONY: help
help: ## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# =============================================================================
# Installation and Environment Setup
# =============================================================================
.PHONY: install-sqlcl
install-sqlcl: ## Install Oracle SQLcl to ~/.local/bin (idempotent)
	@if command -v sql >/dev/null 2>&1; then \
		echo "${OK} SQLcl already installed: $$(sql -V 2>&1 | head -n1)"; \
	else \
		echo "${INFO} Installing Oracle SQLcl..."; \
		uv run python manage.py install sqlcl; \
		echo "${OK} SQLcl installation complete!"; \
	fi

.PHONY: install-uv
install-uv:                                         ## Install latest version of uv (idempotent)
	@if command -v uv >/dev/null 2>&1; then \
		echo "${OK} UV already installed: $$(uv --version)"; \
	else \
		echo "${INFO} Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; \
		echo "${OK} UV installed successfully"; \
	fi

.PHONY: install
install: destroy clean ## Install the project, dependencies, and pre-commit
	@echo "${INFO} Starting fresh installation..."
	@uv python pin 3.12 >/dev/null 2>&1
	@uv venv >/dev/null 2>&1
	@uv sync --all-extras --dev
	@echo "${OK} Installation complete! 🎉"

.PHONY: destroy
# Remove venv and node_modules

destroy:
	@echo "${INFO} Destroying virtual environment... 🗑️"
	@uv run pre-commit clean >/dev/null 2>&1 || true
	@rm -rf .venv
	@rm -rf node_modules
	@echo "${OK} Virtual environment destroyed 🗑️"

# =============================================================================
# Dependency Management
# =============================================================================
.PHONY: upgrade
upgrade: ## Upgrade all dependencies to latest stable versions
	@echo "${INFO} Updating all dependencies... 🔄"
	@uv lock --upgrade
	@echo "${OK} Dependencies updated 🔄"
	@uv run pre-commit autoupdate
	@echo "${OK} Updated Pre-commit hooks 🔄"

.PHONY: lock
lock: ## Rebuild lockfiles from scratch
	@echo "${INFO} Rebuilding lockfiles... 🔄"
	@uv lock --upgrade >/dev/null 2>&1
	@echo "${OK} Lockfiles updated"

# =============================================================================
# Build and Release
# =============================================================================
.PHONY: build
build: ## Build the package
	@echo "${INFO} Building package... 📦"
	@uv build >/dev/null 2>&1
	@echo "${OK} Package build complete"

# =============================================================================
# Cleaning and Maintenance
# =============================================================================
.PHONY: clean
clean: ## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory... 🧹"
	@rm -rf .pytest_cache .ruff_cache .hypothesis build/ -rf dist/ .eggs/ .coverage coverage.xml coverage.json htmlcov/ .pytest_cache tests/.pytest_cache tests/**/.pytest_cache .mypy_cache .unasyncd_cache/ .auto_pytabs_cache >/dev/null 2>&1
	@find . -name '*.egg-info' -exec rm -rf {} + >/dev/null 2>&1
	@find . -type f -name '*.egg' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*.pyc' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*.pyo' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '*~' -exec rm -f {} + >/dev/null 2>&1
	@find . -name '__pycache__' -exec rm -rf {} + >/dev/null 2>&1
	@find . -name '.ipynb_checkpoints' -exec rm -rf {} + >/dev/null 2>&1
	@echo "${OK} Working directory cleaned"

# =============================================================================
# Tests, Linting, Coverage
# =============================================================================
.PHONY: test
test: ## Run the tests
	@echo "${INFO} Running test cases... 🧪"
	@uv run pytest -n 2 --dist=loadgroup tests
	@echo "${OK} Tests complete ✨"

.PHONY: coverage
coverage: ## Run tests with coverage report
	@echo "${INFO} Running tests with coverage... 📊"
	@uv run pytest --cov -n 2 --dist=loadgroup --quiet
	@uv run coverage html >/dev/null 2>&1
	@uv run coverage xml >/dev/null 2>&1
	@echo "${OK} Coverage report generated ✨"

.PHONY: lint
lint: ## Run all linting and type checking
	@echo "${INFO} Running pre-commit checks... 🔎"
	@uv run pre-commit run --color=always --all-files
	@echo "${OK} Pre-commit checks passed ✨"
	@echo "${INFO} Running type checkers... 🔍"
	@uv run mypy app tools manage.py
	@uv run pyright app tools manage.py
	@echo "${OK} All linting and type checks complete ✨"

.PHONY: format
format: ## Run code formatters
	@echo "${INFO} Running code formatters... 🔧"
	@uv run ruff check --fix --unsafe-fixes
	@echo "${OK} Code formatting complete ✨"

.PHONY: mypy
mypy: ## Run mypy type checker using local packages
	@echo "${INFO} Running mypy type checker... 🔍"
	@uv run mypy app tools manage.py
	@echo "${OK} Mypy type checking complete ✨"

.PHONY: pyright
pyright: ## Run pyright type checker using local packages
	@echo "${INFO} Running pyright type checker... 🔍"
	@uv run pyright app tools manage.py
	@echo "${OK} Pyright type checking complete ✨"

.PHONY: typecheck
typecheck: mypy pyright ## Run all type checkers
	@echo "${OK} All type checks complete ✨"

# =============================================================================
# Local Infrastructure (Oracle 23AI Docker)
# =============================================================================
.PHONY: start-infra
start-infra: ## Start local containers
	@echo "${INFO} Starting local Oracle 23AI instance..."
	@uv run python manage.py database oracle start-local-container --recreate
	@echo "${OK} Infrastructure started"

.PHONY: stop-infra
stop-infra: ## Stop local containers
	@echo "${INFO} Stopping local Oracle 23AI instance..."
	@uv run python manage.py database oracle stop-local-container
	@echo "${OK} Infrastructure stopped"

.PHONY: wipe-infra
wipe-infra: ## Remove local container info
	@echo "${INFO} Wiping local Oracle 23AI instance..."
	@uv run python manage.py database oracle wipe-local-container --volumes --force
	@echo "${OK} Infrastructure wiped"

.PHONY: infra-logs
infra-logs: ## Tail development infrastructure logs
	@echo "${INFO} Tailing logs for local Oracle 23AI instance..."
	@uv run python manage.py database oracle local-container-logs --follow
