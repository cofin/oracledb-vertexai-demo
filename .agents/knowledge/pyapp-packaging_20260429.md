# Knowledge Entry: pyapp-packaging_20260429

- **Flow ID:** `pyapp-packaging_20260429`
- **Description:** Saga — PyApp onefile packaging and dual-arch GitHub Releases (linux x86_64 + aarch64) plus a distroless container image.
- **Completed:** 2026-05-02
- **Beads Epic:** `oracledb-vertexai-7dh`
- **Topics:** pyapp, packaging, onefile, release, github-actions, docker, distroless, glibc, cargo-zigbuild, multi-arch

<!-- truth: start -->
## Summary

The repo ships a `coffee` onefile binary built via a custom Bundle-Patch-Compile
path on top of PyApp — not `[tool.pyapp]` or `uvx pyapp build`. The release
pipeline produces native onefiles for `linux/amd64` and `linux/arm64`, plus a
distroless container image that wraps the verified onefile binary. Wallets are
mounted at `/app/wallet` for Oracle wallet-backed deployments.

## Patterns Elevated (see patterns.md for full list)

- Custom Bundle-Patch-Compile path: `tools/bundler.py` builds assets and the wheel, bundles Python 3.13 dependencies, patches PyApp to install under the XDG config directory (`~/.config/cymbal-coffee` by default), then compiles Linux launchers with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17`.
- `make build-onefile` MUST force `UV_PYTHON` / `PYAPP_BUILD_PYTHON` to the explicit CPython 3.13 build interpreter — the repo-local `.python-version` is `3.12` for normal development and `uv run` would otherwise rebuild the env under the wrong interpreter.
- Native arch runners only: `ubuntu-24.04` for x86_64/amd64 and `ubuntu-24.04-arm` for aarch64/arm64. Cross-compile via emulation is rejected — both arches build natively in the matrix.
- Release uploads attach onefiles explicitly: `dist/coffee-linux-x86_64`, `dist/coffee-linux-aarch64`, plus checksums, with `fail_on_unmatched_files: true`. Do not use `dist/*.tar.gz` globs in the upload list — `make build-onefile` writes internal `dist/python-dist-*.tar.gz` bundles that should not ship.
- Single distroless `tools/deploy/docker/Dockerfile`. Allow Docker context access to `dist/coffee-*-linux-gnu` (whitelist in `.dockerignore` against the global `dist/*` ignore). Pre-extract the PyApp runtime with `HOME=/app`. Image entrypoint stays `coffee`.
- Wallet-backed deployments mount Oracle wallets at `/app/wallet`. The image sets `TNS_ADMIN=/app/wallet` and `WALLET_LOCATION=/app/wallet`, exposes the path as a volume, and is run with `-v /path/to/wallet:/app/wallet:ro`.
- Onefile and container smoke checks invoke `coffee upgrade --help` (the packaged end-user command) — not `coffee run --help`. Raw SQLSpec developer commands stay on `python manage.py database ...`.

## GLIBC Compatibility

The verified `dist/coffee` launcher resolves only `GLIBC_2.17` and earlier
symbols — confirmed via `readelf -Ws dist/coffee | rg -o 'GLIBC_[0-9.]+' | sort -Vu | tail`.
Lowering the Python payload platform from `manylinux_2_28` to `manylinux_2_17`
failed on `greenlet==3.5.0` under Python 3.14, so the Python wheels currently
resolve at `manylinux_2_28` even though the launcher binary targets 2.17.

## Key Files

- `tools/bundler.py` — Bundle-Patch-Compile orchestrator.
- `tools/scripts/build-onefile-package.sh` — driver script invoked by `make build-onefile`.
- `Makefile` — `build-onefile` target with `UV_PYTHON`/`PYAPP_BUILD_PYTHON` overrides.
- `.github/workflows/release.yml` — release matrix (native runners per arch) producing onefiles, checksums, and the container image; final job creates the GitHub Release.
- `.github/workflows/ci.yml` — PR checks on both x86_64 and arm64 runners across Python 3.12 / 3.13 / 3.14.
- `tools/deploy/docker/Dockerfile` — single distroless container Dockerfile wrapping the prepared onefile.
- `.dockerignore` — `dist/*` ignored with `dist/coffee-amd64-linux-gnu` and `dist/coffee-arm64-linux-gnu` whitelisted.
- `pyproject.toml` — `requires-python = ">=3.12,<3.15"`; `[dependency-groups.build]`.

## Verification Checklist

`uv lock --check`; focused config tests under Python 3.12, 3.13, and 3.14;
`make build-onefile`; `dist/coffee upgrade --help`; maintainer-only
`dist/coffee run --help`; `readelf -Ws dist/coffee | rg -o 'GLIBC_[0-9.]+' | sort -Vu | tail`;
`uv build`; `git diff --check`; `make lint`; `make test`.
<!-- truth: end -->
