# Flow: pyapp-enablement_20260429

## Specification
This flow focuses on configuring `pyproject.toml` to support `pyapp` and ensuring that the project can be bundled into a functional single-file Linux binary.

### Requirements
- Target Entry Point: `app.__main__:run_cli`
- Target Binary Name: `coffee` (derived from command name)
- Python Version: Pin the PyApp onefile runtime to `3.13` for release-binary
  compatibility; package metadata and CI should still support `3.14` as a
  project runtime.
- Asset Handling: Build assets before packaging and ensure `hatchling` includes the generated `src/app/domain/web/static/dist/` files plus templates, SQL, and public assets.

### Live Repo Findings (2026-05-02)
- `vite.config.ts` already points `litestar-vite-plugin` at package-internal build output: `input=["src/resources/main.js", "src/resources/styles.css"]`, `bundleDir="src/app/domain/web/static/dist"`, `hotFile="src/app/domain/web/static/dist/hot"`, and `resourceDir="src/resources"`. It also sets `publicDir="src/resources/public"` so brand assets copy into the bundle.
- `src/app/lib/settings.py` `ViteSettings.BUNDLE_DIR` defaults to `BASE_DIR / "domain" / "web" / "static" / "dist"`, and `PathConfig` keeps `root=BASE_DIR.parents[1]`, `resource_dir=Path("src/resources")`, and `bundle_dir=self.BUNDLE_DIR`.
- `[tool.hatch.build.targets.wheel].artifacts` already includes the required `**/*.j2`, `**/*.sql`, `**/*.ico`, `**/*.png`, `**/*.svg`, `**/*.css`, `**/*.js`, and `**/*.json` patterns, plus existing `.ini`, `.html`, and `.txt` patterns.
- `Makefile` already exposes `assets-build` as `uv run python manage.py assets build`, and `make build` already runs `manage.py assets build` before `uv build`.
- The repo should use the custom DMA-style Bundle-Patch-Compile PyApp path
  instead of plain `uvx pyapp build`: clone PyApp, bundle Python/dependencies
  with `tools/bundler.py`, patch `src/app.rs` to install under the XDG config
  dir (`~/.config/cymbal-coffee` by default), then compile the binary.
- The onefile build should keep DMA's Linux glibc compatibility strategy:
  compile with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17` and
  require Zig/cargo-zigbuild for Linux release binaries rather than silently
  falling back to a host-glibc build.
- Python 3.14 remains in package metadata and CI coverage, but the PyApp
  embedded runtime is Python 3.13 because the current Python 3.14 dependency
  payload could not resolve against a lower manylinux/glibc wheel floor.
- Because this repo's local `.python-version` is still `3.12`, `make
  build-onefile` must set `UV_PYTHON`/`PYAPP_BUILD_PYTHON` for its assets,
  wheel, and onefile script steps so the release-binary path is built under the
  explicit 3.13 interpreter.
- `[dependency-groups].build` currently contains only `bump-my-version`; keep it
  build-tool-only and do not add PyApp as a Python dependency because the
  custom builder clones the pinned PyApp source directly. Preserve parallel docs
  edits in `pyproject.toml` and `uv.lock`.
- The release Docker image should be onefile-first like the accelerator
  reference: copy `dist/coffee-${TARGETARCH}-linux-gnu` into a distroless
  runtime, pre-extract the PyApp payload with `HOME=/app`, and keep the final
  entrypoint as the `coffee` launcher rather than an internal site-packages
  script.
- Wallet mounting is part of container packaging. The image should include
  `/app/wallet`, set `TNS_ADMIN` and `WALLET_LOCATION` to that path, and expose
  it as a volume so users can mount Autonomous Database wallets read-only at
  runtime.
- `coffee upgrade` is the packaged/end-user install command and should be the
  command used for onefile/container install-path smoke tests. Do not expose
  `coffee downgrade`; raw SQLSpec developer commands live on `manage.py`.

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
- [ ] 2.1 Expand project Python metadata to support Python 3.14 (`requires-python` and classifiers).
- [ ] 2.2 Add a DMA-style `tools/bundler.py` for pre-bundling Python 3.13 and dependencies into a PyApp-ready `python-dist.tar.gz`.
- [ ] 2.3 Add `tools/scripts/build-onefile-package.sh` that pins PyApp, sets `PYAPP_PYTHON_VERSION=3.13`, uses `PYAPP_EXEC_SPEC=app.__main__:run_cli`, patches the install directory to the XDG config path, requires Zig/cargo-zigbuild for Linux glibc 2.17 release builds, forces the onefile build path through explicit `UV_PYTHON`/`PYAPP_BUILD_PYTHON`, supports `PYAPP_BUILD_TARGET` for both `x86_64-unknown-linux-gnu` and `aarch64-unknown-linux-gnu`, and writes `dist/coffee`.
- [ ] 2.4 Keep `[dependency-groups].build` build-tool-only. It may contain release/build tools such as `bump-my-version`, but **must not** accumulate runtime dependencies, frontend packages, PyApp source checkouts, or general install dependencies. Runtime packages stay in `[project.dependencies]`; Node/Vite packages stay in root `package.json`.
- [ ] 2.5 Add `tools/deploy/docker/Dockerfile` and `make
  build-onefile-container` so the release can produce a single distroless
  container from the verified onefile binary. Do not keep separate
  `Dockerfile.canonical`, `Dockerfile.distroless`, or `docker/run` variants.
  Keep `.dockerignore` narrow enough to allow `dist/coffee-amd64-linux-gnu`
  and `dist/coffee-arm64-linux-gnu` into the build context.

### Phase 3: Verification
- [ ] 3.1 Run `make assets-build` to ensure assets land in `src/app/domain/web/static/dist/`.
- [ ] 3.2 Run `uv build` to ensure the wheel is healthy and contains templates, SQL, public assets, and the generated Vite manifest.
- [ ] 3.3 Run `make build-onefile` and verify output in `dist/coffee`.
- [ ] 3.4 Verify the embedded Python distribution and patched install path are generated by `tools/bundler.py`.
- [ ] 3.5 Execute `dist/coffee upgrade --help` and verify the packaged/end-user install command resolves without relying on the source tree.
- [ ] 3.6 Execute `dist/coffee run --help` only as a server-command smoke for maintainers; do not document it as the install/bootstrap command.
- [ ] 3.7 Do **not** add `coffee assets` to the packaged binary. Asset operations live on `python manage.py assets ...` before packaging; the onefile binary should consume prebuilt assets.
- [ ] 3.8 Run `make build-onefile-container`, then smoke test the image with
  `docker run --rm cymbal-coffee:latest upgrade --help`. For wallet-backed deployments,
  verify the supported runtime shape is
  `docker run -v /path/to/wallet:/app/wallet:ro ...`.
