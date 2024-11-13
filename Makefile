SHELL := /bin/bash
# =============================================================================
# Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
USING_PDM		          	=	$(shell grep "tool.pdm" pyproject.toml && echo "yes")
ENV_PREFIX		        	=.venv/bin/
VENV_EXISTS           		=	$(shell python3 -c "if __import__('pathlib').Path('.venv/bin/activate').exists(): print('yes')")
SRC_DIR               		=src
BUILD_DIR             		=dist
PDM_OPTS 		          	?=
PDM 			            ?= 	pdm $(PDM_OPTS)

.EXPORT_ALL_VARIABLES:

ifndef VERBOSE
.SILENT:
endif


.PHONY: help
help: 		   										## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)


.PHONY: upgrade
upgrade:       										## Upgrade all dependencies to the latest stable versions
	@echo "=> Updating all dependencies"
	@if [ "$(USING_PDM)" ]; then $(PDM) update; fi
	@echo "=> Python Dependencies Updated"
	@$(ENV_PREFIX)pre-commit autoupdate
	@echo "=> Updated Pre-commit"

.PHONY: uninstall
uninstall:
	@echo "=> Uninstalling PDM"
ifeq ($(OS),Windows_NT)
	@echo "=> Removing PDM from %APPDATA%\Python\Scripts"
	@if exist "%APPDATA%\Python\Scripts\pdm" (del "%APPDATA%\Python\Scripts\pdm")
else
	@echo "=> Removing PDM from ~/.local/bin"
	@rm -f ~/.local/bin/pdm
endif
	@echo "=> PDM removal complete"
	@echo "=> Uninstallation complete!"

# =============================================================================
# Developer Utils
# =============================================================================
install-pdm: 										## Install latest version of PDM
	@curl -sSLO https://pdm.fming.dev/install-pdm.py && \
	curl -sSL https://pdm.fming.dev/install-pdm.py.sha256 | shasum -a 256 -c - && \
	python3 install-pdm.py

install:											## Install the project and dev deps
	@if ! $(PDM) --version > /dev/null; then echo '=> Installing PDM'; $(MAKE) install-pdm; fi
	@if [ "$(VENV_EXISTS)" ]; then echo "=> Removing existing virtual environment"; fi
	@if [ "$(VENV_EXISTS)" ]; then $(MAKE) destroy-venv && $(MAKE) clean; fi
	@if [ "$(USING_PDM)" ]; then $(PDM) config venv.in_project true && pdm venv --python 3.12 create --force; fi
	@if [ "$(USING_PDM)" ]; then $(PDM) install -G:all; fi
	@echo "=> Install complete! Note: If you want to re-install re-run 'make install'"


.PHONY: clean
clean: ## Remove build, test, and documentation artifacts
	@echo "=> Cleaning project..."
	@rm -rf \
		.coverage coverage.xml coverage.json htmlcov/ \
		.pytest_cache tests/.pytest_cache tests/**/.pytest_cache \
		.mypy_cache .unasyncd_cache/ \
		.ruff_cache .hypothesis build/ dist/ .eggs/
	@find . -name '*.egg-info' -exec rm -rf {} +
	@find . -type f -name '*.egg' -exec rm -f {} +
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -rf {} +
	@find . -name '.ipynb_checkpoints' -exec rm -rf {} +
	@find . -name '.terraform' -exec rm -fr {} +
	@echo "=> Clean complete."

destroy-venv: 											## Destroy the virtual environment
	@echo "=> Cleaning Python virtual environment"
	@rm -rf .venv

destroy-node_modules: 											## Destroy the node environment
	@echo "=> Cleaning Node modules"
	@rm -rf node_modules

tidy: clean destroy-venv destroy-node_modules ## Clean up everything

migrations:       ## Generate database migrations
	@echo "ATTENTION: This operation will create a new database migration for any defined models changes."
	@while [ -z "$$MIGRATION_MESSAGE" ]; do read -r -p "Migration message: " MIGRATION_MESSAGE; done ;
	@$(ENV_PREFIX)app database make-migrations --autogenerate -m "$${MIGRATION_MESSAGE}"

.PHONY: migrate
migrate:          ## Generate database migrations
	@echo "ATTENTION: Will apply all database migrations."
	@$(ENV_PREFIX)app database upgrade

.PHONY: build
build:
	@echo "=> Building package..."
	@if [ "$(USING_PDM)" ]; then pdm build; fi
	@echo "=> Package build complete..."

.PHONY: refresh-lockfiles
refresh-lockfiles:                                 ## Sync lockfiles with requirements files.
	@pdm update --update-reuse --group :all

.PHONY: lock
lock:                                             ## Rebuild lockfiles from scratch, updating all dependencies
	@pdm update --update-eager --group :all

# =============================================================================
# Tests, Linting, Coverage
# =============================================================================
.PHONY: lint
lint: 												## Runs pre-commit hooks; includes ruff linting, codespell, black
	@echo "=> Running pre-commit process"
	@$(ENV_PREFIX)pre-commit run --all-files
	@echo "=> Pre-commit complete"

.PHONY: format
format: 												## Runs code formatting utilities
	@echo "=> Running pre-commit process"
	@$(ENV_PREFIX)ruff . --fix
	@echo "=> Pre-commit complete"

.PHONY: coverage
coverage:  											## Run the tests and generate coverage report
	@echo "=> Running tests with coverage"
	@$(ENV_PREFIX)pytest tests --cov=app
	@$(ENV_PREFIX)coverage html
	@$(ENV_PREFIX)coverage xml
	@echo "=> Coverage report generated"

.PHONY: test
test:  												## Run the tests
	@echo "=> Running test cases"
	@$(ENV_PREFIX)pytest tests
	@echo "=> Tests complete"

# -----------------------------------------------------------------------------
# Local Infrastructure
# -----------------------------------------------------------------------------

.PHONY: start-infra
start-infra: ## Start local containers
	@echo "=> Starting local Oracle 23AI & Valkey instances..."
	@docker compose -f docker-compose.yml up -d --force-recreate

.PHONY: stop-infra
stop-infra: ## Stop local containers
	@echo "=> Stopping local Oracle 23AI & Valkey instances..."
	@docker compose -f docker-compose.yml down

.PHONY: wipe-infra
wipe-infra: ## Remove local container info
	@echo "=> Wiping local Oracle 23AI & Valkey instances..."
	@docker compose -f docker-compose.yml down -v --remove-orphans

.PHONY: infra-logs
infra-logs: ## Tail development infrastructure logs
	@echo "=> Tailing logs for local Oracle 23AI & Valkey instances..."
	@docker compose -f docker-compose.yml logs -f
