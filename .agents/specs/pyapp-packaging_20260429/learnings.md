# Learnings: Build & Release Modernization

## [2026-05-02] - PyApp Bundle-Patch-Compile Completion

- **Implemented:** Custom DMA-style PyApp build using `tools/bundler.py` and
  `tools/scripts/build-onefile-package.sh` instead of `[tool.pyapp]` or
  `uvx pyapp build`.
- **Files changed:** `Makefile`, `tools/bundler.py`,
  `tools/scripts/build-onefile-package.sh`, `.github/workflows/ci.yml`,
  `.github/workflows/release.yml`,
  `tools/deploy/docker/Dockerfile`, `.dockerignore`,
  `pyproject.toml`, `package.json`, `package-lock.json`,
  `src/tests/unit/project/test_build_release_config.py`, and the build/release
  Flow specs.
- **Learnings:**
  - The onefile runtime should be Python 3.13 for this release path. The repo
    can still advertise and test Python 3.14 support, but the PyApp binary uses
    Python Build Standalone 3.13.13 and `PYAPP_PYTHON_VERSION=3.13`.
  - Keep the release build interpreter explicit with `UV_PYTHON`/
    `PYAPP_BUILD_PYTHON`; otherwise `.python-version` (`3.12`) can make
    `uv run` rebuild the environment under Python 3.12 during
    `make build-onefile`. x86_64 release builds use
    `cpython-3.13.12-linux-x86_64-gnu`; arm64 release builds run on native
    `ubuntu-24.04-arm` and request `cpython-3.13.12-linux-aarch64-gnu`.
  - Release CI must use native architecture runners for max support:
    `ubuntu-24.04` for x86_64/amd64 and `ubuntu-24.04-arm` for
    aarch64/arm64. The release matrix builds onefile and container artifacts
    for both architectures before the final GitHub Release job downloads and
    attaches them.
  - For Linux max compatibility, require Zig/cargo-zigbuild and compile PyApp
    with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17`. The verified
    `dist/coffee` launcher only referenced GLIBC symbols through `GLIBC_2.17`.
  - Release uploads should attach the onefiles explicitly as
    `dist/coffee-linux-x86_64` and `dist/coffee-linux-aarch64` plus checksums,
    with `fail_on_unmatched_files: true`. Do not use `dist/*.tar.gz` in the
    release attachment list because `make build-onefile` creates internal
    `dist/python-dist-*.tar.gz` bundles.
  - Install the bundled app under the XDG config directory:
    `~/.config/cymbal-coffee` by default, honoring `XDG_CONFIG_HOME` through
    Rust `directories::BaseDirs.config_dir()`.
  - Build release containers from the verified onefile binary. The distroless
    Dockerfile lives at `tools/deploy/docker/Dockerfile` and expects
    `dist/coffee-${TARGETARCH}-linux-gnu`,
    pre-extracts the PyApp runtime with `HOME=/app`, and keeps the public
    entrypoint as `coffee`.
  - Wallet-backed deployments should mount wallets at `/app/wallet`. The image
    sets `TNS_ADMIN=/app/wallet` and
    `WALLET_LOCATION=/app/wallet`, exposes that path as a volume, and can be run
    with `-v /path/to/wallet:/app/wallet:ro`.
  - `coffee upgrade` is the packaged/end-user install command. Release onefile
    and container smoke checks should use `coffee upgrade --help`; raw SQLSpec
    developer commands such as downgrade/current stay on `python manage.py
    database ...`.
  - `.dockerignore` must not hide the prepared onefile from Docker. Ignore
    `dist/*` but whitelist `dist/coffee-amd64-linux-gnu` and
    `dist/coffee-arm64-linux-gnu`.
  - Python dependency wheels for this app currently resolve at
    `manylinux_2_28`; lowering the Python payload platform to
    `manylinux_2_17` failed on `greenlet==3.5.0` under Python 3.14.
- **Verification:** `uv lock --check`; focused config tests under Python 3.12,
  3.13, and 3.14; `make build-onefile`; `dist/coffee upgrade --help`;
  maintainer-only `dist/coffee run --help`; `readelf -Ws dist/coffee | rg -o 'GLIBC_[0-9.]+' |
  sort -Vu | tail`; `uv build`; `git diff --check`; `make lint`; `make test`.
