# Master PRD: Build & Release Modernization

## Context
The project currently uses `hatchling` and `uv` for builds, but lacks an automated release process and standalone binaries. This saga modernizes the delivery pipeline by enabling `pyapp` for onefile binary packaging and implementing a robust GitHub Actions release workflow.

**Saga ID:** `pyapp-packaging_20260429`
**Beads Master Epic:** `oracledb-vertexai-7dh`

## Roadmap

### Chapter 1: `pyapp-enablement`
**ID:** `pyapp-enablement_20260429`
**Beads Epic:** `oracledb-vertexai-7dh.1`

**Goal:** Configure `pyproject.toml` to support `pyapp` and verify local binary generation.
- Use the custom DMA-style PyApp Bundle-Patch-Compile path targeting
  `app.__main__:run_cli`; do not use `[tool.pyapp]` or plain `uvx pyapp build`
  for this release path.
- Pin the PyApp onefile runtime to Python 3.13 for release-binary
  compatibility while keeping Python 3.14 as a project-supported runtime in
  metadata and CI.
- Verify `make build-onefile` produces a functional `dist/coffee` binary.
- Ensure all static assets (SQL, J2, icons) are correctly bundled in the onefile state.

### Chapter 2: `release-automation`
**ID:** `release-automation_20260429`
**Beads Epic:** `oracledb-vertexai-7dh.2`

**Goal:** Implement a GitHub Actions workflow that automates the full release cycle.
- Trigger on `v*` tag pushes.
- Automate version bumping via `bump-my-version` (coordinated with tag).
- Build and upload:
    - Wheel (`.whl`)
    - Source Distribution (`.tar.gz`)
    - Linux x86_64 Onefile Binary (`coffee-linux-x86_64`)
    - Linux aarch64 Onefile Binary (`coffee-linux-aarch64`)
    - Linux amd64 loadable Docker image (`coffee-image-amd64.tar`) built from
      the matching onefile binary
    - Linux arm64 loadable Docker image (`coffee-image-arm64.tar`) built from
      the matching onefile binary
- Automatically generate release notes and publish to GitHub Releases.

## Global Constraints
- **Zero-Downtime Releases:** Artifacts must be fully verified before the release is published.
- **Platform Consistency:** The PyApp bundle MUST use Python 3.13, Linux
  onefile releases MUST compile through Zig/cargo-zigbuild for glibc 2.17
  launcher targets on x86_64 and aarch64, and CI MUST exercise both the 3.13
  release runtime and the 3.14 project support contract on x86_64 and arm64
  runners.
- **Asset Integrity:** Onefile binaries MUST include all `[tool.hatch.build.targets.wheel.artifacts]` patterns.
- **Container Parity:** Release Docker images MUST wrap the verified onefile
  binary, expose `/app/wallet` for read-only Oracle wallet mounts, and default
  `TNS_ADMIN`/`WALLET_LOCATION` to that path.
- **Workflow Security:** Use `permissions: contents: write` only where necessary for the release process.
