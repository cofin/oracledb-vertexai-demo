# Learnings — `web-and-shell-demo-recordings-and-docs`

## VHS Shell & Playwright Browser Demo Recorders (`tools/demos/`)

- **Optional Dependency Group Invocation (`--group demos`)**: `[dependency-groups].demos = ["playwright>=1.50"]` is intentionally excluded from `dev` (`default-groups`) so `make install` and `make docs` do not pull Playwright into standard builds. Any CLI wrapper or documentation command that invokes Playwright (`make docs-demos-web`, `tools/scripts/record-live-demos.sh`, `manage.py demos check`, `manage.py demos all`) must run via `uv run --group demos ...`; bare `uv run` re-syncs `.venv` to `default-groups` and strips `playwright`.
- **Up-Front Combined Prerequisite Preflight**: `manage.py demos all` (`demos_all` in `tools/demos/cli.py`) validates both `verify_vhs_prerequisites()` and `verify_web_prerequisites()` before executing any live VHS tape so missing Playwright or FFmpeg installations fail immediately without running partial live recordings against `adb-free` and Vertex AI.
- **Headless Chromium Discovery & Cleanup**:
  - Go `rod` inside `vhs` requires `ROD_BROWSER_BIN` when `/usr/bin/google-chrome` is absent (resolved across `ROD_BROWSER_BIN`, system `PATH`, and `~/.cache/ms-playwright/chromium-*/chrome-linux/chrome`) plus `VHS_NO_SANDBOX=true`.
  - Playwright `record_video_dir` against local `adb-free:latest-26ai` (`https://localhost:8443/ords/apex`) requires `ignore_https_errors=True`, matched `1280x720` `viewport` and `record_video_size`, explicit `context.close()` before reading `page.video.path()`, and separate `try ... finally: browser.close()` around context teardown so Chromium always exits cleanly even on navigation errors.

## Documentation Accuracy & OKF Hygiene

- **Automated Public & Agent Drift Guards**: `src/tests/unit/tools/test_docs_accuracy.py` (for `README.md`, `CONTRIBUTING.md`, `SLIDES.md`, `src/apex/README.md`, `src/app/db/migrations/README.md`, and `docs/**/*.md`) and `src/tests/unit/test_okf_layout.py` (for `AGENTS.md`, `.agents/AGENTS.md`, `src/tests/**/AGENTS.md`, `.agents/bundles/{product,knowledge}/**/*.md`, and `.agents/skills/**/*.md`) enforce repository path resolution, `Makefile` target existence, OKF YAML frontmatter (`type`, `title`, `description`), retired-symbol bans, and public-repo anonymization (zero workstation paths, internal shortlinks, Drive/Slides document URLs, or credential tokens).
