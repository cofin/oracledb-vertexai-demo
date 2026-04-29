# Flow: pyapp-enablement_20260429

## Specification
This flow focuses on configuring `pyproject.toml` to support `pyapp` and ensuring that the project can be bundled into a functional single-file Linux binary.

### Requirements
- Target Entry Point: `app.__main__:run_cli`
- Target Binary Name: `coffee` (derived from command name)
- Python Version: Pin to `3.12`
- Asset Handling: Ensure `nodeenv` and `hatchling` correctly include all static assets in the build.

## Implementation Plan

### Phase 1: Frontend Asset Alignment
- [ ] 1.1 Update `src/js/vite.config.ts` to output inside the Python package.
  ```ts
  build: {
    outDir: path.resolve(__dirname, "../py/app/server/static/dist"),
    emptyOutDir: true,
  },
  ```
- [ ] 1.2 Verify `src/py/app/lib/settings.py` `ViteSettings.BUNDLE_DIR` matches this path.

### Phase 2: Configuration
- [ ] 2.1 Add `[tool.pyapp]` section to `pyproject.toml`.
  ```toml
  [tool.pyapp]
  package = "app"
  module = "app.__main__"
  function = "run_cli"
  python-version = "3.12"
  ```
- [ ] 2.2 Add `pyapp` to the `build` dependency group in `pyproject.toml`.
  ```toml
  [dependency-groups]
  build = ["bump-my-version", "pyapp"]
  ```

### Phase 3: Verification
- [ ] 3.1 Run `make assets-build` to ensure assets land in the correct package directory.
- [ ] 3.2 Run `uv build` to ensure the wheel is healthy and contains assets.
- [ ] 3.3 Run `uvx pyapp build` and verify output in `dist/`.
- [ ] 3.4 Rename `dist/app` to `dist/coffee`.
- [ ] 3.5 Execute `dist/coffee --help` and verify output.
- [ ] 3.6 Execute `dist/coffee assets build` to ensure the bundled binary can still perform asset operations if needed.
