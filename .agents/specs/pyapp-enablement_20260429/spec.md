# Flow: pyapp-enablement_20260429

## Specification
This flow focuses on configuring `pyproject.toml` to support `pyapp` and ensuring that the project can be bundled into a functional single-file Linux binary.

### Requirements
- Target Entry Point: `app.__main__:run_cli`
- Target Binary Name: `coffee` (derived from command name)
- Python Version: Pin to `3.12`
- Asset Handling: Build assets before packaging and ensure `hatchling` includes the generated `src/app/domain/web/static/dist/` files plus templates, SQL, and public assets.

## Implementation Plan

### Phase 1: Frontend Asset Alignment
- [ ] 1.1 Verify the root `vite.config.ts` already outputs into the Python package:
  ```ts
  litestar({
    input: ["src/resources/main.js", "src/resources/styles.css"],
    bundleDir: "src/app/domain/web/static/dist",
    hotFile: "src/app/domain/web/static/dist/hot",
    resourceDir: "src/resources",
  })
  ```
- [ ] 1.2 Verify `src/app/lib/settings.py` `ViteSettings.BUNDLE_DIR` matches `src/app/domain/web/static/dist` and that `PathConfig(resource_dir=Path("src/resources"))` is still set.
- [ ] 1.3 Confirm `[tool.hatch.build.targets.wheel].artifacts` includes `**/*.j2`, `**/*.sql`, `**/*.ico`, `**/*.png`, `**/*.svg`, `**/*.css`, `**/*.js`, and `**/*.json`.

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
- [ ] 2.3 Keep `[dependency-groups].build` build-tool-only. It may contain release/build tools such as `bump-my-version` and `pyapp`, but **must not** accumulate runtime dependencies, frontend packages, or general install dependencies. Runtime packages stay in `[project.dependencies]`; Node/Vite packages stay in root `package.json`.

### Phase 3: Verification
- [ ] 3.1 Run `make assets-build` to ensure assets land in `src/app/domain/web/static/dist/`.
- [ ] 3.2 Run `uv build` to ensure the wheel is healthy and contains templates, SQL, public assets, and the generated Vite manifest.
- [ ] 3.3 Run `uvx pyapp build` and verify output in `dist/`.
- [ ] 3.4 Rename `dist/app` to `dist/coffee`.
- [ ] 3.5 Execute `dist/coffee --help` and verify output.
- [ ] 3.6 Execute `dist/coffee run --help` and verify the bundled CLI can resolve the app module without relying on the source tree.
- [ ] 3.7 Do **not** add `coffee assets` to the packaged binary. Asset operations live on `python manage.py assets ...` before packaging; the onefile binary should consume prebuilt assets.
