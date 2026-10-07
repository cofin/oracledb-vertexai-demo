# Project Log

Historical change log and completed milestone record for Cymbal Coffee.

## 2026-10-07: Flow Setup & OKF v0.2 Migration
- Transitioned framework from legacy Beads tracker to beadless OKF v0.2 knowledge bundles under `.agents/bundles/`.
- Scaffolding: `product/`, `knowledge/`, `specs/`, `research/`, `log.md`, `index.md`.
- Consolidated legacy `flows.md` and archived milestones into `log.md`.
- Synthesized `knowledge/workflow.md` from canonical template with project-native commands (`make test`, `make lint`, `make typecheck`).
- Partitioned legacy `patterns.md` into evidence-backed chapters under `knowledge/patterns/` (`architecture.md`, `code-style.md`, `testing.md`, `operations.md`).
- Migrated component knowledge guides to `knowledge/guides/`.
- Reorganized active specs to `.agents/bundles/specs/` (`apex-ops-console`, `apex-ops-app`, `apex-demo-verification-docs`, `vhs-demo-recordings_20260429`).
- Promoted research `research_apex26_ords_apexlang_schema_bridge` into `apex-ops-console` spec bundle.
- Removed legacy tracker machinery (`.beads/`, `.agents/beads.json`, `.git/hooks/pre-commit`).

## 2026-06-26: Explore Search UX Fixes
- `fix-explore-search-ux`: Resolved explore page search usability issues by aligning query parameter to `query` and handling form submission in HTMX.

## 2026-06-24: Cloud Run & ORDS Deployment Labs
- `cloudrun-gce-lab`: Shipped Cloud Run app readiness, GCE Oracle DB appliance, Cloud Build + Cloud Run deploy pipeline, renamed current lab to GCE-only, and authored new Cloud Run lab module with verification.
- `cloudrun-ords-deploy`: Deployed ORDS to Cloud Run stateless, peered via Direct VPC, utilizing Secret Manager for system password, enabling REST APIs against private GCE database VM.
- `adk2-sqlspec-migration`: Integrated SQLSpec ADK 2.0 store contract (singular table names, `append_event` history) and updated default model to `gemini-3.1-flash-lite`.

## 2026-06-23: Oracle APEX Integration & Lab Hardening
- `oracle-apex-integration`: Implemented APEX media staging, idempotent install/upgrade engine + `infra apex` CLI, ORDS sidecar, and APEXlang source for operations console.
- `oracle-schema-annotations`: Verified 26ai schema annotations using `USER_ANNOTATIONS_USAGE`.
- `inventory`: Seeded store inventory data, deterministic availability routing, inventory-aware vector search (RAG), live HTMX inventory UI, and coordinate/privacy guidance.
- `demo-simplification`: Consolidated settings, streamlined AI chat to SSE streaming, improved ADK readability, added Maps directions, split frontend modules, and simplified test suites.

## 2026-05-02: PyApp Packaging & Reset Milestones
- `pyapp-packaging_20260429`: Shipped Bundle-Patch-Compile path, cargo-zigbuild GLIBC 2.17 launchers, distroless Dockerfile, and dual-architecture GitHub Releases matrix.
- `store-location-inventory-chat_20260501`: Store coordinates, Haversine nearest-store queries, stock availability routing, browser location opt-in, and no-key Google Maps URLs.
- `cymbal-coffee-reset_20260429`: Foundation bump, domain service restructure, ADK 2 runner, HTMX + Vite frontend, vector calculator, and test reorganization.
