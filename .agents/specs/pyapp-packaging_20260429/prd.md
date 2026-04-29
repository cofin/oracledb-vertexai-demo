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
- Configure `[tool.pyapp]` targeting `app.__main__:run_cli`.
- Pin Python version to 3.12 for consistent bundling.
- Verify `uvx pyapp build` produces a functional `dist/app` binary.
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
- Automatically generate release notes and publish to GitHub Releases.

## Global Constraints
- **Zero-Downtime Releases:** Artifacts must be fully verified before the release is published.
- **Platform Consistency:** The PyApp bundle MUST use Python 3.12.
- **Asset Integrity:** Onefile binaries MUST include all `[tool.hatch.build.targets.wheel.artifacts]` patterns.
- **Workflow Security:** Use `permissions: contents: write` only where necessary for the release process.
