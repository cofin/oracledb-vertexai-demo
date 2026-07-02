# Operations & Packaging Guide

This guide details the PyApp onefile binary packaging, container builds, release CI pipeline, and Sphinx documentation.

## PyApp Onefile Packaging

The project ships a self-contained onefile binary named `coffee` built via PyApp.
- **Workflow:** We use a custom **Bundle-Patch-Compile** path rather than standard `[tool.pyapp]` or `uvx pyapp build`.
- **Execution Script:** `tools/bundler.py` coordinates:
  1. Compiles frontend assets into `src/app/domain/web/static/`.
  2. Builds the Python application wheel.
  3. Bundles Python 3.13 dependencies.
  4. Patches PyApp to install runtime files under the XDG configuration directory (`~/.config/cymbal-coffee` by default).
  5. Compiles launcher binaries using `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17` to target GLIBC 2.17 compatibility.
- **Python Version Override:** Development uses Python 3.12 (set in `.python-version`), but the onefile target runs Python 3.13. `make build-onefile` overrides `UV_PYTHON`/`PYAPP_BUILD_PYTHON` to force CPython 3.13 compilation.
- **GLIBC Compatibility Check:** Validate the resulting launcher to verify no higher GLIBC symbols are resolved:
  ```bash
  readelf -Ws dist/coffee | rg -o 'GLIBC_[0-9.]+' | sort -Vu | tail
  ```

## Container Deployment

The production container is defined in `tools/deploy/docker/Dockerfile`.
- **Distroless Base:** It wraps the onefile binary on top of a distroless runtime, avoiding standard Python image overhead.
- **Context:** The build requires access to the compiled onefile launcher under `dist/`. Ensure `.dockerignore` whitelists `dist/coffee-*-linux-gnu` against the global `dist/*` ignore rule.
- **Wallet Mounts:** Oracle Wallets are mounted at `/app/wallet`. The Dockerfile configures:
  - `TNS_ADMIN=/app/wallet`
  - `WALLET_LOCATION=/app/wallet`
  The container must be run with a read-only wallet volume mount:
  ```bash
  docker run -v /local/wallet:/app/wallet:ro ...
  ```

## Release CI Pipeline

The GitHub Action workflows under `.github/workflows/` automate release creation:
- **Native Matrix:** Cross-compilation via QEMU is rejected. Builds run on native architecture runners:
  - `ubuntu-24.04` for `amd64/x86_64`
  - `ubuntu-24.04-arm` for `arm64/aarch64`
- **Release Artifacts:** Uploads attach specific binaries: `dist/coffee-linux-x86_64`, `dist/coffee-linux-aarch64`, plus checksums. Do not upload internal `dist/python-dist-*.tar.gz` bundles.
- **Smoke Check:** The release verification test triggers `coffee upgrade --help` (not `coffee run`) to verify installation functionality.

## Sphinx Documentation Portal

The developer learning portal is built via Sphinx.
- **Theme:** Uses `sphinx-immaterial` theme (not `shibuya`) with custom admonitions `tour-stop`, `oracle-internals`, and `agent-detail` defined in `conf.py`.
- **Information Architecture:** A locked, three-tier structure:
  1. Hero: `index.md` + walkthrough `tour.md`.
  2. Concepts: exactly 3 pages under `concepts/` (vector-search, rag, agent-flow).
  3. Reference: `reference/` (quickstart, cli, api, internals, developers).
- **Code Embeds:** Always embed code using `literalinclude` with anchors in source files (e.g. `# docs:start-<name>` and `# docs:end-<name>`). Do not copy-paste code inline. Include a short framing sentence naming the file and class.
- **Autodoc Scope:** Restricted to public entrypoints: `ADKRunner`, `CacheService`, `MetricsService`, `ProductService`, and domain schemas packages. Do not auto-document settings, CLI command definitions, or IoC providers.
