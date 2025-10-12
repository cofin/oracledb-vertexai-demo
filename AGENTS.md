# Repository Guidelines

## Project Structure & Module Organization

The Litestar demo application lives in `app/`: `app/server/` exposes routes and view models, `app/services/` contains chat and recommendation logic, `app/db/` wraps SQLSpec data access, and `app/cli/` powers `uv run app ...` commands. Shared integrations sit in `app/lib/` and utilities in `app/utils/`. Architecture guides and screenshots are under `docs/`, automation scripts in `tools/`, and tests grouped by scope in `tests/api/`, `tests/integration/`, and `tests/unit/`. Use `manage.py` for environment setup, database orchestration, and diagnostics.

## Build, Test, and Development Commands

Use UV-managed workflows to ensure consistent dependencies:

```bash
make install-uv                      # install astral's UV
make install                         # sync deps and pre-commit hooks
uv run manage.py init --run-install  # bootstrap .env and install prerequisites
make start-infra                     # launch Oracle 23AI via Docker or Podman
uv run app load-fixtures             # seed sample data and prebuilt embeddings
uv run app run                       # start the demo server on http://localhost:5006
```

Run `uv run manage.py doctor` after upgrades, and `make build` to produce distributable artifacts.

## Coding Style & Naming Conventions

Target Python 3.11+ with full type hints; `mypy --strict`, `pyright`, and `ruff` (line length 120) are enforced via pre-commit. Prefer snake_case for modules, functions, and CLI commands, PascalCase for classes, and UPPER_SNAKE_CASE for constants. Keep route handlers lean, delegating persistence to `app/db` repositories and orchestration to `app/services`.

## Testing Guidelines

Pytest with asyncio and xdist backs the suite. Run `make test` or `uv run pytest -n 2 --dist=loadgroup tests` before submitting changes to mirror CI. Place new tests alongside the feature in `tests/unit/`, `tests/api/`, or `tests/integration/`; name files `test_<feature>.py` and fixtures in `tests/conftest.py`. Use `make coverage` when touching database or vector search logic to confirm regressions are prevented.

## Commit & Pull Request Guidelines

History follows Conventional Commits (`feat:`, `fix:`, `chore:`). Write imperative subjects under 72 characters and include scope details or issue references in the body. For PRs, summarize functional impact, link relevant docs, attach screenshots or curl output for UI/API updates, and list verification commands (`make lint`, `make test`, `uv run app run`). Flag reviewers when changes affect Oracle wallet handling or Vertex AI integration.

## Configuration & Secrets

Generate local configuration with `uv run manage.py init`; the resulting `.env` stays untracked. Replace the sample `service_account.json` with project-specific credentials and keep secrets out of the repository. When using Autonomous Database wallets, extract them via `uv run manage.py database oracle wallet extract Wallet_*.zip` and store artifacts in ignored directories.
