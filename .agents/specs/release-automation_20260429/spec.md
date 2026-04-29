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
- [ ] 2.1 Configure `bump-my-version` in `pyproject.toml` to synchronize version strings across the entire stack.
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
  filename = "src/py/app/__init__.py"
  search = '__version__ = "{current_version}"'
  replace = '__version__ = "{new_version}"'

  [[tool.bumpversion.files]]
  filename = "manage.py"
  search = 'version="{current_version}"'
  replace = 'version="{new_version}"'

  [[tool.bumpversion.files]]
  filename = "src/py/app/server/core.py"
  search = 'version="{current_version}"'
  replace = 'version="{new_version}"'

  [[tool.bumpversion.files]]
  filename = "src/js/package.json"
  search = '"version": "{current_version}"'
  replace = '"version": "{new_version}"'
  ```
- [ ] 2.2 Verify GITHUB_TOKEN permissions in the workflow (`contents: write`).

### Phase 3: Dry Run
- [ ] 3.1 Verify the workflow syntax using `action-lint` or similar if available.
- [ ] 3.2 (Manual) Confirm with user that secret-less releases are acceptable for the first iteration.
