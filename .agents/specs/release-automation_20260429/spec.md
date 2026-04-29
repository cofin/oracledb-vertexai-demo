# Flow: release-automation_20260429

## Specification
Automate the distribution of library and binary artifacts via GitHub Actions. The workflow should manage version synchronization and publish to GitHub Releases upon tag creation.

### Requirements
- CI Trigger: Push to tags matching `v*`.
- Artifacts:
    - `.whl` and `.tar.gz` via `uv build`.
    - `coffee-linux-x86_64` onefile binary via `pyapp build`.
- Automation:
    - Use `softprops/action-gh-release@v2`.
    - Use `astral-sh/setup-uv` for fast builds.

## Implementation Plan

### Phase 1: Workflow Development
- [ ] 1.1 Create `.github/workflows/release.yml`.
  ```yaml
  name: Release

  on:
    push:
      tags:
        - 'v*'

  jobs:
    build-and-release:
      runs-on: ubuntu-latest
      permissions:
        contents: write
      steps:
        - uses: actions/checkout@v4
          with:
            fetch-depth: 0

        - name: Install uv
          uses: astral-sh/setup-uv@v5
          with:
            enable-cache: true

        - name: Set up Python
          run: uv python install 3.12

        - name: Install project and frontend dependencies
          run: |
            uv sync --group build
            uv run python manage.py assets install

        - name: Build frontend assets
          run: uv run python manage.py assets build

        - name: Build Wheel and SDist
          run: uv build

        - name: Build PyApp Onefile
          run: |
            uvx pyapp build
            mv dist/app dist/coffee-linux-x86_64

        - name: Create Release
          uses: softprops/action-gh-release@v2
          if: startsWith(github.ref, 'refs/tags/')
          with:
            files: |
              dist/*.whl
              dist/*.tar.gz
              dist/coffee-linux-x86_64
            generate_release_notes: true
  ```
- [ ] 1.2 Implement tag-triggered logic as shown in the template.

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
