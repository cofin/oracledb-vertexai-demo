# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

SHELL := /bin/bash

# =============================================================================
# Configuration and Environment Variables
# =============================================================================

.DEFAULT_GOAL := help
.ONESHELL:
.SHELLFLAGS := -e -o pipefail -c
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory
PYAPP_BUILD_PYTHON ?= cpython-3.13.12-linux-x86_64-gnu
PYAPP_BUILD_TARGET ?=
FRONTEND_DIR := src/resources

# Detect Rodete and configure public package indexes
ifneq ($(shell grep -s -q "rodete" /etc/os-release && echo "yes"),)
export NPM_CONFIG_REGISTRY=https://registry.npmjs.org
export PIP_INDEX_URL=https://pypi.org/simple
export UV_INDEX_URL=https://pypi.org/simple
endif

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

.PHONY: setup-env
setup-env:                                          ## Configure local environment (e.g. Rodete)
	@./tools/scripts/setup-env.sh

.PHONY: install
install: destroy clean setup-env install-uv ## Install the project and its dependencies (pre-commit / prek hooks are NOT auto-installed — run `uvx prek install` manually if you want commit-time checks).
	@set -e
	@echo "${INFO} Starting fresh installation..."
	@uv python pin 3.12 >/dev/null 2>&1
	@uv venv >/dev/null 2>&1
	@uv sync --all-extras --dev
	@echo "${INFO} Installing frontend packages... 📦"
	@uv run python manage.py assets install >/dev/null 2>&1
	@echo "${INFO} Building frontend assets... 📦"
	@uv run python manage.py assets build
	@echo "${OK} Installation complete! 🎉"
	@echo "${INFO} Tip: run \`uvx prek install\` if you want pre-commit hooks active on git commit (not required — \`make lint\` runs the full check on demand)."

.PHONY: destroy
# Remove venv and node_modules

destroy:
	@echo "${INFO} Destroying virtual environment... 🗑️"
	@uvx prek clean >/dev/null 2>&1 || true
	@rm -rf .venv
	@rm -rf node_modules
	@rm -rf $(FRONTEND_DIR)/node_modules
	@echo "${OK} Virtual environment destroyed 🗑️"

# =============================================================================
# Dependency Management
.PHONY: upgrade
upgrade: setup-env ## Upgrade all dependencies to latest stable versions
	@echo "${INFO} Updating all dependencies... 🔄"

	@uv lock --upgrade
	@echo "${INFO} Updating frontend dependencies... 🔄"
	@(cd $(FRONTEND_DIR) && npx --yes npm-check-updates@latest --target latest --upgrade && npm install --no-fund)
	@echo "${OK} Dependencies updated 🔄"
	@uvx prek autoupdate
	@echo "${OK} Updated prek hooks 🔄"


.PHONY: lock
lock: ## Rebuild lockfiles from scratch
	@echo "${INFO} Rebuilding lockfiles... 🔄"
	@uv lock --upgrade >/dev/null 2>&1
	@cd $(FRONTEND_DIR) && npm install --package-lock-only >/dev/null 2>&1
	@echo "${OK} Lockfiles updated"

# =============================================================================
# Build and Release
# =============================================================================
.PHONY: build
build: ## Build the package (Python wheel + frontend assets)
	@echo "${INFO} Building frontend assets... 📦"
	@uv run python manage.py assets build >/dev/null 2>&1
	@echo "${INFO} Building Python package... 📦"
	@uv build >/dev/null 2>&1
	@echo "${OK} Package build complete"

.PHONY: release
release: ## Bump version and refresh release lockfiles (bump=major|minor|patch|pre)
	@if [ -z "$(bump)" ]; then \
		echo "${ERROR} Usage: make release bump=major|minor|patch|pre"; \
		exit 1; \
	fi
	@echo "${INFO} Preparing release bump ($(bump))... 📦"
	@$(MAKE) clean
	@uv run bump-my-version bump $(bump)
	@uv lock --upgrade-package app >/dev/null 2>&1
	@echo "${OK} Release bump complete 🎉"

.PHONY: pre-release
pre-release: ## Start a pre-release: make pre-release version=0.3.0-alpha.1
	@if [ -z "$(version)" ]; then \
		echo "${ERROR} Usage: make pre-release version=X.Y.Z-alpha.N"; \
		echo ""; \
		echo "Pre-release workflow:"; \
		echo "  1. Start alpha:     make pre-release version=0.3.0-alpha.1"; \
		echo "  2. Next alpha:      make pre-release version=0.3.0-alpha.2"; \
		echo "  3. Move to beta:    make pre-release version=0.3.0-beta.1"; \
		echo "  4. Move to rc:      make pre-release version=0.3.0-rc.1"; \
		echo "  5. Final release:   make release bump=pre"; \
		exit 1; \
	fi
	@echo "${INFO} Preparing pre-release $(version)... 🧪"
	@$(MAKE) clean
	@uv run bump-my-version bump --new-version $(version) pre
	@uv lock --upgrade-package app >/dev/null 2>&1
	@echo "${OK} Pre-release $(version) complete 🧪"

.PHONY: build-wheel
build-wheel: assets-build ## Build the Python wheel with bundled frontend assets
	@echo "${INFO} Building Python wheel... 📦"
	@uv build --wheel >/dev/null 2>&1
	@echo "${OK} Wheel build complete"

.PHONY: build-onefile
build-onefile: ## Build the self-contained PyApp onefile
	@set -e
	UV_PYTHON="$(PYAPP_BUILD_PYTHON)" $(MAKE) build-wheel
	echo "${INFO} Building onefile with Python $(PYAPP_BUILD_PYTHON)... 🔨"
	PYAPP_BUILD_PYTHON="$(PYAPP_BUILD_PYTHON)" PYAPP_BUILD_TARGET="$(PYAPP_BUILD_TARGET)" UV_PYTHON="$(PYAPP_BUILD_PYTHON)" ./tools/scripts/build-onefile-package.sh
	echo "${OK} Onefile build complete"

.PHONY: build-onefile-container
build-onefile-container: build-onefile ## Build the distroless container from the onefile binary
	$(eval ARCH := $(shell uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/'))
	@set -e
	cp dist/coffee dist/coffee-$(ARCH)-linux-gnu
	trap 'rm -f dist/coffee-$(ARCH)-linux-gnu' EXIT
	echo "${INFO} Building distroless onefile container for $(ARCH)..."
	docker build \
		-f tools/deploy/docker/Dockerfile \
		-t cymbal-coffee:latest \
		-t cymbal-coffee:dev \
		--build-arg TARGETARCH=$(ARCH) \
		.
	echo "${OK} Container image built: cymbal-coffee:latest"

# =============================================================================
# Documentation
# =============================================================================
.PHONY: docs
docs: ## Build the Sphinx documentation site (warnings as errors)
	@echo "${INFO} Building docs... 📚"
	@uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
	@echo "${OK} Docs built at docs/_build/html/index.html"

.PHONY: docs-serve
docs-serve: ## Serve docs with hot reload on http://localhost:8002
	@echo "${INFO} Serving docs on http://localhost:8002 (hot reload)... 📚"
	@uv run --group docs sphinx-autobuild --port 8002 --watch src docs docs/_build/html

.PHONY: docs-clean
docs-clean: ## Remove built documentation
	@echo "${INFO} Cleaning docs build... 🧹"
	@rm -rf docs/_build
	@echo "${OK} Docs build removed"

# =============================================================================
# Cleaning and Maintenance
# =============================================================================
.PHONY: clean
clean: ## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory... 🧹"
	@rm -rf .pytest_cache .ruff_cache .hypothesis build/ -rf dist/ .eggs/ .coverage coverage.xml coverage.json htmlcov/ .pytest_cache src/tests/.pytest_cache src/tests/**/.pytest_cache .mypy_cache .unasyncd_cache/ .auto_pytabs_cache >/dev/null 2>&1
	@rm -rf src/app/domain/web/static .litestar.json src/resources/.litestar.json node_modules/.vite tsconfig.tsbuildinfo $(FRONTEND_DIR)/.vite $(FRONTEND_DIR)/tsconfig.tsbuildinfo >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '*.egg-info' -exec rm -rf {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -type f -name '*.egg' -exec rm -f {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '*.pyc' -exec rm -f {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '*.pyo' -exec rm -f {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '*~' -exec rm -f {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '__pycache__' -exec rm -rf {} + >/dev/null 2>&1
	@find . \( -path './.envs' -o -path './.git' -o -path './.venv' -o -path './node_modules' \) -prune -o -name '.ipynb_checkpoints' -exec rm -rf {} + >/dev/null 2>&1
	@echo "${OK} Working directory cleaned"

# =============================================================================
# Tests, Linting, Coverage
# =============================================================================
.PHONY: test
test: ## Run the tests
	@echo "${INFO} Running test cases... 🧪"
	@set -e; uv run pytest -n 2 --dist=loadgroup src/tests
	@echo "${OK} Tests complete ✨"

.PHONY: coverage
coverage: ## Run tests with coverage report
	@echo "${INFO} Running tests with coverage... 📊"
	@uv run pytest --cov -n 2 --dist=loadgroup --quiet
	@uv run coverage html >/dev/null 2>&1
	@uv run coverage xml >/dev/null 2>&1
	@echo "${OK} Coverage report generated ✨"

.PHONY: lint
lint: ## Run all linting and type checking (Python + frontend)
	@echo "${INFO} Running prek (pre-commit) checks... 🔎"
	@uvx prek run --color=always --all-files
	@echo "${OK} prek checks passed ✨"
	@echo "${INFO} Running type checkers... 🔍"
	@uv run mypy src/app tools manage.py
	@uv run pyright src/app tools manage.py
	@$(MAKE) frontend-typecheck
	@echo "${OK} All linting and type checks complete ✨"

.PHONY: format
format: ## Run code formatters
	@echo "${INFO} Running code formatters... 🔧"
	@uv run ruff check --fix --unsafe-fixes
	@echo "${OK} Code formatting complete ✨"

.PHONY: mypy
mypy: ## Run mypy type checker using local packages
	@echo "${INFO} Running mypy type checker... 🔍"
	@uv run mypy src/app tools manage.py
	@echo "${OK} Mypy type checking complete ✨"

.PHONY: pyright
pyright: ## Run pyright type checker using local packages
	@echo "${INFO} Running pyright type checker... 🔍"
	@uv run pyright src/app tools manage.py
	@echo "${OK} Pyright type checking complete ✨"

.PHONY: typecheck
typecheck: mypy pyright ## Run all type checkers
	@echo "${OK} All type checks complete ✨"

# =============================================================================
# Frontend and Assets
# =============================================================================
.PHONY: assets-build
assets-build: ## Build assets via Litestar assets CLI
	@echo "${INFO} Building assets via manage.py... 📦"
	@uv run python manage.py assets build
	@echo "${OK} Assets build complete ✨"

.PHONY: frontend-typecheck
frontend-typecheck: ## Run frontend TypeScript type checks
	@echo "${INFO} Running frontend type checks... 🔍"
	@cd $(FRONTEND_DIR) && npx tsc --noEmit
	@echo "${OK} Frontend type checks complete ✨"

# =============================================================================
# App Runtime
# =============================================================================
.PHONY: init
init: ## Initialize local environment (.env)
	@echo "${INFO} Initializing project environment..."
	@uv run manage.py init
	@echo "${OK} Initialization complete"

.PHONY: doctor
doctor: ## Verify local prerequisites and project health
	@echo "${INFO} Running diagnostics..."
	@uv run manage.py doctor
	@echo "${OK} Diagnostics complete"

.PHONY: migrate
migrate: ## Run database migrations
	@echo "${INFO} Running database migrations..."
	@uv run python manage.py database upgrade --no-prompt
	@echo "${OK} Migrations complete"

.PHONY: load-fixtures
load-fixtures: ## Load sample fixture data
	@echo "${INFO} Loading sample fixtures..."
	@uv run coffee load-fixtures
	@echo "${OK} Fixtures loaded"

.PHONY: run
run: ## Start the application server
	@echo "${INFO} Starting application..."
	@uv run coffee run

.PHONY: bootstrap
bootstrap: install init doctor start-infra migrate load-fixtures ## One-shot local bootstrap (except app run)
	@echo "${OK} Bootstrap complete. Run 'make run' to start the app."

# =============================================================================
# Local Infrastructure (Oracle 26ai Docker)
# =============================================================================
.PHONY: start-infra
start-infra: ## Start local Oracle container (DB only; run `make apex` separately for APEX)
	@echo "${INFO} Starting local Oracle 26ai instance..."
	@uv run python manage.py infra start --recreate --skip-apex --skip-ords
	@echo "${OK} Infrastructure started (APEX skipped — run 'make apex' to install/upgrade it)"

.PHONY: apex
apex: ## Install/upgrade APEX in the DB and start the ORDS sidecar container (slow; not run automatically)
	@echo "${INFO} Installing/upgrading Oracle APEX + ORDS — this can take several minutes... ⏳"
	@uv run python manage.py infra start
	@echo "${OK} APEX + ORDS ready"

.PHONY: stop-infra
stop-infra: ## Stop local containers
	@echo "${INFO} Stopping local Oracle 26ai instance..."
	@uv run python manage.py infra stop
	@echo "${OK} Infrastructure stopped"

.PHONY: wipe-infra
wipe-infra: ## Remove local container info
	@echo "${INFO} Wiping local Oracle 26ai instance..."
	@uv run python manage.py infra wipe --volumes --force --yes
	@echo "${OK} Infrastructure wiped"

.PHONY: infra-logs
infra-logs: ## Tail development infrastructure logs
	@echo "${INFO} Tailing logs for local Oracle 26ai instance..."
	@uv run python manage.py infra logs --follow
