# Progress: Build & Release Modernization

| Chapter | ID | Beads | Status |
| :--- | :--- | :--- | :--- |
| **Ch 1** | `pyapp-enablement_20260429` | `oracledb-vertexai-7dh.1` | ✅ Complete |
| **Ch 2** | `release-automation_20260429` | `oracledb-vertexai-7dh.2` | ✅ Complete |

## Milestone Log
- [2026-04-29] PRD initialized and roadmap established.
- [2026-05-02] Live repo findings synced into `pyapp-enablement_20260429/spec.md` and `release-automation_20260429/spec.md`: asset output and runtime version metadata are already aligned; remaining work is `pyapp`, bump-version config, and tag-triggered release workflow.
- [2026-05-02] Python 3.14 support accepted as part of build/release modernization for project metadata and CI coverage, but the PyApp onefile runtime moved back to Python 3.13 for release-binary compatibility.
- [2026-05-02] CI should request explicit non-free-threaded CPython 3.14 (`cpython-3.14.3-linux-x86_64-gnu` / `cpython-3.14.3-linux-aarch64-gnu`) because a bare `3.14` selector can choose free-threaded `3.14t` in local `uv` resolution; release onefile builds should request explicit available CPython 3.13 selectors (`cpython-3.13.12-linux-x86_64-gnu` / `cpython-3.13.12-linux-aarch64-gnu`) while the embedded distribution uses the Python Build Standalone 3.13.13 archive.
- [2026-05-02] Multi-architecture correction: PR CI should run package/unit checks on both `ubuntu-24.04` x86_64 and `ubuntu-24.04-arm` arm64 runners. Tag release CI should build and upload `coffee-linux-x86_64`, `coffee-linux-aarch64`, `coffee-image-amd64.tar`, and `coffee-image-arm64.tar` plus checksums.
- [2026-05-02] Linux onefile builds should require Zig/cargo-zigbuild and target glibc 2.17 with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17`; plain `cargo build` is acceptable only for non-Linux local builds.
- [2026-05-02] `make build-onefile` must override `.python-version` with `UV_PYTHON`/`PYAPP_BUILD_PYTHON` so assets, wheel, and onefile packaging run under explicit Python 3.13 instead of the repo-local Python 3.12 pin.
- [2026-05-02] Build and release modernization completed: Beads `oracledb-vertexai-7dh`, `.1`, and `.2` were closed after local verification (`make build-onefile`, binary help smoke tests, GLIBC_2.17 symbol check, `uv build`, `make lint`, `make test`).
- [2026-05-02] Release uploads should attach onefile binaries explicitly as `dist/coffee-linux-x86_64` and `dist/coffee-linux-aarch64` plus checksums, enable `fail_on_unmatched_files`, and scope source distributions to `dist/app-*.tar.gz` so `dist/python-dist-*.tar.gz` remains an internal build input.
- [2026-05-02] Revision: accelerator-style Dockerfile support is now in scope.
  The distroless release image wraps the verified onefile binary, exports
  `coffee-image-amd64.tar` and `coffee-image-arm64.tar` plus checksums as release assets, and reserves
  `/app/wallet` with `TNS_ADMIN`/`WALLET_LOCATION` for read-only Oracle wallet
  mounts.
- [2026-05-02] Dockerfile path flattened: the release image now uses the single
  distroless onefile Dockerfile at `tools/deploy/docker/Dockerfile`; the old
  `tools/deploy/docker/run/` variants should remain deleted.
- [2026-05-02] CLI correction: `coffee upgrade` is the packaged/end-user
  install command and should be used for release smoke checks. Raw SQLSpec
  developer commands such as downgrade/current stay under `python manage.py
  database ...`; `coffee downgrade` should not be exposed.
