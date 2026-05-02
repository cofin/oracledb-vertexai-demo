# Flow: release-automation_20260429

## Specification
Automate the distribution of library and binary artifacts via GitHub Actions. The workflow should manage version synchronization and publish to GitHub Releases upon tag creation.

### Requirements
- CI Trigger: Push to tags matching `v*`.
- Artifacts:
    - `.whl` and `.tar.gz` via `uv build`.
    - `coffee-linux-x86_64` and `coffee-linux-aarch64` onefile binaries via
      the custom PyApp builder.
    - `coffee-image-amd64.tar` and `coffee-image-arm64.tar` loadable Docker
      images built from the matching onefile binaries.
- Automation:
    - Use `softprops/action-gh-release@v2`.
    - Use `astral-sh/setup-uv` for fast builds.

### Live Repo Findings (2026-05-02)
- Runtime version literal consolidation is already implemented: `src/app/__init__.py`, `src/app/cli/main.py`, `src/app/server/core.py`, and `manage.py` all consume `app.__metadata__.__version__`; `app.__metadata__` falls back to `pyproject.toml` when the package is not installed.
- `pyproject.toml` is already at project version `0.2.0`, but `package.json` has no `"version"` field yet. Add `"version": "0.2.0"` before enabling the `package.json` bump target.
- `[tool.bumpversion]` is not configured yet. The bump target should stay limited to `pyproject.toml` and `package.json`; do not add app module files now that they import the metadata module.
- `.github/workflows/release.yml` does not exist yet. There are no tracked workflow files under `.github/workflows/` in the current checkout.
- `pyproject.toml` and `uv.lock` currently include uncommitted docs dependency work from the parallel docs effort. Release automation implementation must preserve that shared state while adding build/release configuration.
- Python 3.14 is now part of project support scope, but the onefile release
  runtime is Python 3.13 for binary compatibility. The release job should
  install/sync explicit CPython 3.13 selectors
  (`cpython-3.13.12-linux-x86_64-gnu` /
  `cpython-3.13.12-linux-aarch64-gnu`) before building the PyApp binary.
  Regular CI should include Python 3.13 for release runtime coverage and Python
  3.14 for forward project support; use explicit non-free-threaded 3.14
  selectors (`cpython-3.14.3-linux-x86_64-gnu` /
  `cpython-3.14.3-linux-aarch64-gnu`) because a bare `3.14` selector can
  resolve to free-threaded `3.14t` locally.
- Linux release binaries should install Zig/cargo-zigbuild and compile PyApp
  with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17`; do not publish
  a host-glibc fallback binary.
- The GitHub release must attach onefile binaries explicitly. Build
  `dist/coffee`, copy it to `dist/coffee-linux-x86_64` or
  `dist/coffee-linux-aarch64` from the release matrix, assert it is non-empty,
  generate the matching `.sha256`, and set
  `fail_on_unmatched_files: true` on `softprops/action-gh-release`. Keep the
  sdist glob scoped to `dist/app-*.tar.gz` so the internal
  `dist/python-dist-*.tar.gz` bundle is not uploaded as a release artifact.
- Release CI should use native architecture runners for max support:
  `ubuntu-24.04` for x86_64/amd64 and `ubuntu-24.04-arm` for
  aarch64/arm64. PR CI should also run unit/package checks on both x86_64 and
  arm64 runners.
- The accelerator reference also builds a distroless container from the PyApp
  onefile. Bring that into scope here with
  `tools/deploy/docker/Dockerfile`, a `make
  build-onefile-container` target, a CI release step that exports
  `dist/coffee-image-amd64.tar`, `dist/coffee-image-arm64.tar`, and checksums
  beside them.
- Keep this as a single release Dockerfile. Do not keep separate
  `Dockerfile.canonical`, `Dockerfile.distroless`, or `tools/deploy/docker/run`
  variants.
- Wallet use must be mount-friendly. The release container should create
  `/app/wallet`, expose it as a volume, and set `TNS_ADMIN=/app/wallet` plus
  `WALLET_LOCATION=/app/wallet` so an Autonomous Database wallet can be mounted
  read-only without rebuilding the image.
- Container smoke tests should verify the packaged/end-user install command
  with `coffee upgrade --help`. Raw SQLSpec developer commands remain on
  `python manage.py database ...`; do not add `coffee downgrade`.

## Implementation Plan

### Phase 1: Workflow Development
- [ ] 1.1 Create `.github/workflows/release.yml` with three jobs:
  ```yaml
  name: Release

  on:
    push:
      tags:
        - 'v*'

  jobs:
    build-python-package:
      runs-on: ubuntu-24.04
      # Build and upload dist/app-*.whl plus dist/app-*.tar.gz.

    build-release-artifacts:
      runs-on: ${{ matrix.runner }}
      strategy:
        matrix:
          include:
            - label: linux-x86_64
              runner: ubuntu-24.04
              python-version: cpython-3.13.12-linux-x86_64-gnu
              rust-target: x86_64-unknown-linux-gnu
              docker-arch: amd64
              onefile-asset: dist/coffee-linux-x86_64
              container-asset: dist/coffee-image-amd64.tar
            - label: linux-aarch64
              runner: ubuntu-24.04-arm
              python-version: cpython-3.13.12-linux-aarch64-gnu
              rust-target: aarch64-unknown-linux-gnu
              docker-arch: arm64
              onefile-asset: dist/coffee-linux-aarch64
              container-asset: dist/coffee-image-arm64.tar
      # Build PyApp with PYAPP_BUILD_TARGET, smoke `coffee upgrade --help`,
      # build the matching Docker image from tools/deploy/docker/Dockerfile,
      # smoke the image, save the image tar, and upload all four files plus
      # checksums as workflow artifacts.

    create-release:
      needs: [build-python-package, build-release-artifacts]
      permissions:
        contents: write
      # Download all workflow artifacts and publish the GitHub Release with
      # fail_on_unmatched_files: true.
  ```
- [ ] 1.2 Implement tag-triggered logic as shown in the template.
- [ ] 1.3 Add a CI workflow with a Python matrix that includes the `3.13`
  release runtime and `3.14` project support on both x86_64 and arm64 runners;
  the job should install/sync the matching interpreter, run unit tests, build
  frontend assets, and build the Python package.

### Phase 2: Configuration Integration
- [ ] 2.1 First collapse runtime version literals to the existing metadata module instead of bumping multiple source files:
  - `src/app/__init__.py` re-exports `__version__` from `app.__metadata__`.
  - `src/app/cli/main.py` imports `__version__` and passes it to `@click.version_option`.
  - `src/app/server/core.py` imports `__version__` and passes it to `OpenAPIConfig(version=...)`.
  - `manage.py` imports `__version__` after it adds `src/` to `sys.path` and passes it to `@click.version_option`.
  - Smoke: `uv run coffee --version`, `uv run python manage.py --version`, and OpenAPI schema generation all report the same value.
- [ ] 2.2 Configure `bump-my-version` in `pyproject.toml` to bump project metadata files only, not app-module literals. `pyproject.toml` is the Python package source of truth; `uv.lock` is refreshed by `uv lock`; root `package.json` is fine as a frontend metadata mirror. If `package.json` still lacks `"version"`, add `"version": "0.2.0"` before enabling this bump target.
  ```toml
  [tool.bumpversion]
  current_version = "0.2.0"
  parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
  serialize = ["{major}.{minor}.{patch}"]
  search = "{current_version}"
  replace = "{new_version}"
  regex = false
  ignore_missing_version = false
  tag = true
  sign_tags = false
  tag_name = "v{new_version}"
  tag_message = "bump version: {current_version} → {new_version}"
  allow_dirty = false
  commit = true
  message = "bump version: {current_version} → {new_version}"
  commit_args = ""

  [[tool.bumpversion.files]]
  filename = "pyproject.toml"
  search = 'version = "{current_version}"'
  replace = 'version = "{new_version}"'

  [[tool.bumpversion.files]]
  filename = "package.json"
  search = '"version": "{current_version}"'
  replace = '"version": "{new_version}"'
  ```
- [ ] 2.3 Do **not** add `src/app/__init__.py`, `src/app/server/core.py`, `src/app/cli/main.py`, or `manage.py` to `bump-my-version`. Those files should import/re-export `app.__metadata__.__version__` instead.
- [ ] 2.4 Run `uv lock` after version bumps so `uv.lock` reflects the new project metadata.
- [ ] 2.5 Verify GITHUB_TOKEN permissions in the workflow (`contents: write`).

### Phase 3: Dry Run
- [ ] 3.1 Verify the workflow syntax using `action-lint` or similar if available.
- [ ] 3.2 (Manual) Confirm with user that secret-less releases are acceptable for the first iteration.
