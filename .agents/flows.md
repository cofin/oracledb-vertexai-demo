# Flow Registry

This file tracks all PRDs (Product Requirements Documents) for the project. Each PRD has its own detailed plan in its respective folder.

## [x] PRD: cloudrun-gce-lab
*Link: [./archive/cloudrun-gce-lab/](./archive/cloudrun-gce-lab/)*
*Beads: oracledb-vertexai-jw0 (master epic)*
*Research: [./research/research_cloudrun_gce_lab_overhaul/](./research/research_cloudrun_gce_lab_overhaul/)*

New "real deployment" lab: Litestar webapp on Cloud Run + Oracle 26ai on a
private GCE VM + a Cloud Build deploy pipeline over a private VPC. Additive; the
current single-VM lab is preserved as the GCE-only path.

### Chapters
- [x] **Chapter 1: Cloud Run app/image readiness (`cloudrun-app-readiness`)** — implemented, archived locally 2026-06-24
  *Beads: oracledb-vertexai-jw0.1*
- [x] **Chapter 2: GCE Oracle DB appliance (`gce-oracle-appliance`)** — implemented, archived locally 2026-06-24
  *Link: [./archive/gce-oracle-appliance/](./archive/gce-oracle-appliance/)* · *Beads: oracledb-vertexai-jw0.2*
- [x] **Chapter 3: Cloud Build + Cloud Run deploy pipeline (`cloudbuild-cloudrun-pipeline`)** — implemented, archived locally 2026-06-24
  *Link: [./archive/cloudbuild-cloudrun-pipeline/](./archive/cloudbuild-cloudrun-pipeline/)* · *Beads: oracledb-vertexai-jw0.3*
- [x] **Chapter 4: Rename current lab to GCE-only (`lab-gce-rename`)** — implemented, archived locally 2026-06-24
  *Beads: oracledb-vertexai-jw0.4*
- [x] **Chapter 5: Author new Cloud Run lab module (`cloudrun-lab-authoring`)** — implemented, archived locally 2026-06-24
  *Link: [./archive/cloudrun-lab-authoring/](./archive/cloudrun-lab-authoring/)* · *Beads: oracledb-vertexai-jw0.5*
- [x] **Chapter 6: Cloud Run lab verification + teardown (`cloudrun-lab-verification-teardown`)** — implemented, archived locally 2026-06-24
  *Beads: oracledb-vertexai-jw0.6*

---

## [x] PRD: adb-podman-lab-hardening
*Link: [./specs/adb-podman-lab-hardening/](./specs/adb-podman-lab-hardening/)*
*Beads: oracledb-vertexai-9p5 (master epic)*
*Research: [./research/research_adb_hooks_ux_lab/](./research/research_adb_hooks_ux_lab/)*

### Chapters
- [x] **Chapter 1: ADB-Free vector-memory startup hardening + podman/OL runtime validation (`adb-vector-memory-hardening`)** — superseded by gvenzl revert; archived locally 2026-06-23
  *Beads: oracledb-vertexai-9p5.1*
- [x] **Chapter 2: Lab overhaul — Oracle Linux + podman + accuracy fixes (`oraclelinux-podman-lab`)** — skipped in favor of CoS direct deploy; archived locally 2026-06-24
  *Link: [./specs/oraclelinux-podman-lab/](./specs/oraclelinux-podman-lab/)*
  *Beads: oracledb-vertexai-9p5.2*
- [x] **Chapter 3: UI UX/correctness fixes (`ui-quality-fixes`)** — completed, archived locally 2026-06-23
  *Beads: oracledb-vertexai-9p5.3*

---

## [~] PRD: apex-ops-console
*Link: [./specs/apex-ops-console/](./specs/apex-ops-console/)*
*Beads: oracledb-vertexai-apxo (master epic)*
*Research: [./research/research_apex26_ords_apexlang_schema_bridge/](./research/research_apex26_ords_apexlang_schema_bridge/)*
*Related: `apex-gvenzl-install`*

Post-research roadmap for a source-controlled APEX 26.1 demo app, APEX REST
Source Catalog/OpenAPI bridge, and current Antigravity/MCP configuration
examples. This PRD is not Gemini CLI migration support; it replaces old Gemini
CLI config writes with clean Antigravity config paths.

### Chapters
- [x] **Chapter 1: APEX runtime hardening and Flow reconciliation (`apex-runtime-hardening`)** — done; archived locally 2026-06-23
  *Beads: oracledb-vertexai-apxo.1*
- [x] **Chapter 2: SQLcl 26.1.2 APEXlang lifecycle (`apexlang-lifecycle`)** — implemented and archived locally 2026-06-23
  *Beads: oracledb-vertexai-apxo.2*
- [x] **Chapter 3: APEX-safe coffee data API and OpenAPI contract (`apex-ops-api`)** — implemented and archived locally 2026-06-23
  *Link: [./specs/apex-ops-api/](./specs/apex-ops-api/)* · *Beads: oracledb-vertexai-apxo.3*
- [x] **Chapter 4: Schema bridge and Antigravity MCP configuration (`apex-schema-bridge`)** — implemented and archived locally 2026-06-23
  *Link: [./specs/apex-schema-bridge/](./specs/apex-schema-bridge/)* · *Beads: oracledb-vertexai-apxo.4*
- [~] **Chapter 5: Cymbal Coffee APEX Operations Console app (`apex-ops-app`)** — SQL-backed source app complete; REST Source Catalog import round trip blocked
  *Link: [./specs/apex-ops-app/](./specs/apex-ops-app/)* · *Beads: oracledb-vertexai-apxo.5*
- [ ] **Chapter 6: APEX demo verification and docs (`apex-demo-verification-docs`)** — implementation-ready, blocked by Ch1-Ch5
  *Link: [./specs/apex-demo-verification-docs/](./specs/apex-demo-verification-docs/)* · *Beads: oracledb-vertexai-apxo.6*

---

## [ ] PRD: adk2-sqlspec-migration
*Link: [./specs/adk2-sqlspec-migration/](./specs/adk2-sqlspec-migration/)*
*Beads: oracledb-vertexai-6uc (master epic)*
*Upstream: [litestar-org/sqlspec#525](https://github.com/litestar-org/sqlspec/pull/525)*

Migrate Cymbal Coffee to SQLSpec's ADK 2 store contract using the open SQLSpec
branch while it is unmerged, and update the default chat/classifier model to
`gemini-3.1-flash-lite`.

### Chapters
- [ ] **Chapter 1: Dependency source (`adk2-dependency-source`)** — draft
  *Beads: oracledb-vertexai-6uc.1*
- [ ] **Chapter 2: Store contract (`adk2-store-contract`)** — draft
  *Beads: oracledb-vertexai-6uc.3*
- [ ] **Chapter 3: Gemini 3.1 Flash-Lite default (`gemini31-flash-lite-default`)** — draft
  *Beads: oracledb-vertexai-6uc.4*
- [ ] **Chapter 4: Oracle verification + release cleanup (`adk2-oracle-verification-release-cleanup`)** — draft
  *Beads: oracledb-vertexai-6uc.2*

---

## [ ] PRD: cloudrun-ords-deploy
*Link: [./specs/cloudrun-ords-deploy/](./specs/cloudrun-ords-deploy/)*
*Beads: oracledb-vertexai-ords (master epic)*
*Research: [./research/research_ords_cloudrun_deploy/](./research/research_ords_cloudrun_deploy/)*

Deploy Oracle REST Data Services (ORDS) on Google Cloud Run to provide a scalable,
serverless HTTP front-end for the GCE database, enabling Oracle APEX applications
and REST APIs.

### Chapters
- [ ] **Chapter 1: Image Re-hosting and script prep (`ords-image-prep`)** — planned
  *Beads: oracledb-vertexai-ords.2*
- [ ] **Chapter 2: Terraform Infrastructure (`ords-terraform`)** — planned, depends on Ch1
  *Beads: oracledb-vertexai-ords.3*
- [ ] **Chapter 3: Pipeline Integration (`ords-pipeline`)** — planned, depends on Ch2
  *Beads: oracledb-vertexai-ords.4*
- [ ] **Chapter 4: Lab Walkthrough & Verification (`ords-lab-walkthrough`)** — planned, depends on Ch3
  *Beads: oracledb-vertexai-ords.5*

---

## [ ] PRD: vhs-demo-recordings_20260429
*Link: [./specs/vhs-demo-recordings_20260429/](./specs/vhs-demo-recordings_20260429/)*
*Beads: not created - review gate before implementation*

## Archived

Archived specs are disposable local history and may be ignored or removed from
the repository. Durable learnings belong in `.agents/knowledge/` and
`.agents/patterns.md`; do not point active Flow guidance at archive paths.

- `demo-source-organization_20260501` (`oracledb-vertexai-8jt`) completed and
  archived locally on 2026-05-02.
- `ruff-copyright-modernization` (`oracledb-vertexai-a0l`) completed and
  archived locally on 2026-05-02. SPDX-FileCopyrightText migration shipped in
  b0e9819 + aa221a8; canonical header form and tooling chain are documented in
  `.agents/patterns.md` and `.agents/code-styleguides/python.md`.
- `pyapp-packaging_20260429` (`oracledb-vertexai-7dh`) completed and archived
  locally on 2026-05-02. Both chapters (`pyapp-enablement_20260429`,
  `release-automation_20260429`) shipped the Bundle-Patch-Compile path,
  cargo-zigbuild GLIBC 2.17 launchers, the distroless Dockerfile at
  `tools/deploy/docker/Dockerfile`, and the dual-arch GitHub Releases matrix.
  Durable guidance lives in `.agents/patterns.md`.
- `store-location-inventory-chat_20260501` (`oracledb-vertexai-f6u`) completed
  and archived locally on 2026-05-02. All five chapters closed in Beads on
  2026-05-01 with verification on commit 8fb40b4 (12 focused maps/settings
  tests + 274 full-suite tests). Store data, query services, intent routing,
  browser-location/maps UI, and Maps security/docs are all documented in
  `.agents/knowledge/guides/architecture.md`, `.agents/knowledge/project-guide.md`,
  and `.agents/knowledge/guides/adk-agent-patterns.md`.
- `cymbal-coffee-reset_20260429` (`oracledb-vertexai-4d6`) — master PRD
  closed in Beads 2026-05-02; all nine chapters complete. Knowledge entry:
  `.agents/knowledge/cymbal-coffee-reset_20260429.md`. Per-chapter knowledge
  entries that have their own files: htmx-vite-frontend_20260429 (Ch 4),
  vector-calculator_20260429 (Ch 7), documentation-setup_20260429 (Ch 6),
  ui-regression-recovery_20260501 (corrective), test-suite-reorganization_20260501
  (corrective). Other chapters (foundation-bump, domain-service-restructure,
  adk2-runner, prune-and-document) are summarized in the master entry; their
  durable patterns are in `.agents/patterns.md` and
  `.agents/knowledge/guides/`.
- `oracle-apex-integration` (`oracledb-vertexai-apex`) completed and archived
  locally on 2026-06-23 after Beads recorded closed runtime verification on
  2026-06-13. Current local Oracle guidance lives in `.agents/patterns.md`,
  `.agents/knowledge/project-guide.md`, `.agents/knowledge/guides/architecture.md`,
  and `.agents/knowledge/guides/oracle-vector-search.md`.
- `demo-simplification` (`oracledb-vertexai-mzm`) completed and archived
  locally on 2026-06-23 after Beads recorded all 10 chapters closed on
  2026-06-15. It also absorbed and archived
  `settings-config-consolidation_20260501`. Durable outcomes include docs
  accuracy, dead-code removal, settings/AI/chat consolidation, stream-only
  chat, ADK readability, Maps directions, frontend module split, and test
  simplification; current guidance lives in `.agents/patterns.md` and the
  `.agents/knowledge/` guide set.
- `inventory` (`oracledb-vertexai-inv`) completed and archived locally on
  2026-06-23. All four chapters are closed in Beads: `inventory-data`
  (`oracledb-vertexai-invdata`), `inventory-grounding`
  (`oracledb-vertexai-invground`), `inventory-rag`
  (`oracledb-vertexai-invrag`), and `inventory-ui`
  (`oracledb-vertexai-invui`). Store inventory data, deterministic availability
  routing, inventory-aware vector search (RAG), live HTMX inventory UI, and
  coordinate/privacy guidance are synthesized in
  `.agents/knowledge/project-guide.md` and `.agents/patterns.md`.
- `ui-quality-fixes` (`oracledb-vertexai-9p5.3`) completed and archived
  locally on 2026-06-23 while the parent `adb-podman-lab-hardening` PRD remains
  active. Durable UI/testing guidance is already in `.agents/patterns.md`,
  `.agents/knowledge/guides/architecture.md`, and
  `.agents/knowledge/project-guide.md`.
- `adb-vector-memory-hardening` (`oracledb-vertexai-9p5.1`) was superseded by
  the gvenzl/oracle-free revert and archived locally on 2026-06-23. Current
  vector-memory behavior is the hook-based path in `tools/oracle/on_init/` and
  `tools/oracle/on_startup/`, documented in
  `.agents/knowledge/guides/oracle-vector-search.md`.
- `oracle-schema-annotations` completed and archived locally on 2026-06-23. All chapters (schema-annotations-ddl, schema-annotations-docs, schema-annotations-verification) closed with verification. Annotations are verified on Oracle 26ai using USER_ANNOTATIONS_USAGE dictionary view.
- `apex-media-staging` (`oracledb-vertexai-apxg.1`) completed and archived
  locally on 2026-06-23. Durable APEX media/ORDS image-serving guidance is in
  `.agents/patterns.md`.
- `apex-install-upgrade` (`oracledb-vertexai-apxg.2`) completed and archived
  locally on 2026-06-23. Durable APEX install/upgrade CLI guidance is in
  `.agents/patterns.md`.
- `apex-ords-sidecar` (`oracledb-vertexai-apxg.3`) completed and archived
  locally on 2026-06-23 after final CLI task 3.5 was reconciled into
  `apex-runtime-hardening`.
- `apex-runtime-hardening` (`oracledb-vertexai-apxo.1`) completed and archived
  locally on 2026-06-23. Current ORDS version/readiness/lifecycle guidance is
  synthesized in `.agents/patterns.md`; live Oracle smoke is carried by
  `apex-demo-verification-docs`.
- `apexlang-lifecycle` (`oracledb-vertexai-apxo.2`) completed and archived
  locally on 2026-06-23. Current APEXlang lifecycle guidance is in
  `.agents/patterns.md`; live Oracle round-trip smoke is carried by
  `apex-demo-verification-docs`.
- `apexlang-source` (`oracledb-vertexai-apxg.4`) was absorbed by
  `apexlang-lifecycle` (`oracledb-vertexai-apxo.2`) on 2026-06-23. Current
  APEXlang lifecycle guidance uses SQLcl 26.1.2+, `manage.py infra apex
  generate|export|validate|import`, and `src/apex/cymbal-coffee-ops/` with
  SQLcl-generated hyphenated directories such as `shared-components/` and
  `supporting-objects/`.
- `apex-gvenzl-install` (`oracledb-vertexai-apxg`) master PRD archived locally on
  2026-06-23 after Flow reconciliation. Ch1-Ch4 shipped (media staging,
  idempotent install/upgrade engine + `infra apex` CLI, ORDS sidecar, APEXlang
  source) and are individually archived; Ch5 (`apex-verify-docs`,
  `oracledb-vertexai-apxg.5`) was reconciled with its settings/unit gates closed
  and its remaining smoke/docs/final verification deferred to
  `apex-demo-verification-docs` (`oracledb-vertexai-apxo.6`). Durable
  APEX/ORDS/APEXlang guidance lives in `.agents/patterns.md`.
