# Flow Registry

This file tracks all PRDs (Product Requirements Documents) for the project. Each PRD has its own detailed plan in its respective folder.

## [~] PRD: adb-podman-lab-hardening
*Link: [./specs/adb-podman-lab-hardening/](./specs/adb-podman-lab-hardening/)*
*Beads: oracledb-vertexai-9p5 (master epic)*
*Research: [./research/research_adb_hooks_ux_lab/](./research/research_adb_hooks_ux_lab/)*

### Chapters
- [x] **Chapter 1: ADB-Free vector-memory startup hardening + podman/OL runtime validation (`adb-vector-memory-hardening`)** — superseded by gvenzl revert; archived locally 2026-06-23
  *Beads: oracledb-vertexai-9p5.1*
- [ ] **Chapter 2: Lab overhaul — Oracle Linux + podman + accuracy fixes (`oraclelinux-podman-lab`)** — draft; needs revision after gvenzl revert
  *Link: [./specs/oraclelinux-podman-lab/](./specs/oraclelinux-podman-lab/)*
  *Beads: oracledb-vertexai-9p5.2*
- [x] **Chapter 3: UI UX/correctness fixes (`ui-quality-fixes`)** — completed, archived locally 2026-06-23
  *Beads: oracledb-vertexai-9p5.3*

---

## [~] PRD: apex-gvenzl-install
*Link: [./specs/apex-gvenzl-install/](./specs/apex-gvenzl-install/)*
*Beads: oracledb-vertexai-apxg (master epic)*
*Research: [./research/research_apex_upgrade/](./research/research_apex_upgrade/)*

Install/upgrade Oracle APEX 26.1 + ORDS into the reverted `gvenzl/oracle-free` container via
`manage.py infra apex`, and adopt APEXlang source at `src/apex/`. Precondition: container base
revert (adb-free → gvenzl) owned by a separate agent (task `oracledb-vertexai-2q0`).

### Chapters (Ch1 done; Ch2–Ch5 specced, gated on gvenzl revert)
- [x] **Chapter 1: APEX media staging (`apex-media-staging`)** — done (32 tests; commits 56cb007..1c157c6)
  *Link: [./specs/apex-media-staging/](./specs/apex-media-staging/)*
  *Beads: oracledb-vertexai-apxg.1 (5/5 tasks closed)*
- [x] **Chapter 2: APEX install/upgrade engine + infra apex CLI (`apex-install-upgrade`)** — done (29 tests; commits 31c444f..427a091; database.py untouched)
  *Link: [./specs/apex-install-upgrade/](./specs/apex-install-upgrade/)*
  *Beads: oracledb-vertexai-apxg.2 (5/5 tasks closed)*
- [ ] **Chapter 3: ORDS sidecar runtime via Python CLI (`apex-ords-sidecar`)** — implementation-ready, blocked by Ch1+Ch2
  *Link: [./specs/apex-ords-sidecar/](./specs/apex-ords-sidecar/)*
  *Beads: oracledb-vertexai-apxg.3 (5 tasks)*
- [ ] **Chapter 4: APEXlang source layout + export/import (`apexlang-source`)** — implementation-ready, blocked by Ch2+Ch3
  *Link: [./specs/apexlang-source/](./specs/apexlang-source/)*
  *Beads: oracledb-vertexai-apxg.4 (5 tasks)*
- [ ] **Chapter 5: Verification, settings alignment & docs (`apex-verify-docs`)** — implementation-ready, blocked by Ch2+Ch4
  *Link: [./specs/apex-verify-docs/](./specs/apex-verify-docs/)*
  *Beads: oracledb-vertexai-apxg.5 (5 tasks)*

---

## [ ] PRD: apex-ops-console
*Link: [./specs/apex-ops-console/](./specs/apex-ops-console/)*
*Beads: oracledb-vertexai-apxo (master epic)*
*Research: [./research/research_apex26_ords_apexlang_schema_bridge/](./research/research_apex26_ords_apexlang_schema_bridge/)*
*Related: `apex-gvenzl-install`*

Post-research roadmap for a source-controlled APEX 26.1 demo app, APEX REST
Source Catalog/OpenAPI bridge, and current Antigravity/MCP configuration
examples. This PRD is not Gemini CLI migration support; it replaces old Gemini
CLI config writes with clean Antigravity config paths.

### Chapters
- [ ] **Chapter 1: APEX runtime hardening and Flow reconciliation (`apex-runtime-hardening`)** — implementation-ready, related to `apex-gvenzl-install`
  *Link: [./specs/apex-runtime-hardening/](./specs/apex-runtime-hardening/)* · *Beads: oracledb-vertexai-apxo.1*
- [ ] **Chapter 2: SQLcl 26.1.2 APEXlang lifecycle (`apexlang-lifecycle`)** — implementation-ready, blocked by Ch1
  *Link: [./specs/apexlang-lifecycle/](./specs/apexlang-lifecycle/)* · *Beads: oracledb-vertexai-apxo.2*
- [ ] **Chapter 3: APEX-safe coffee data API and OpenAPI contract (`apex-ops-api`)** — implementation-ready, blocked by Ch1
  *Link: [./specs/apex-ops-api/](./specs/apex-ops-api/)* · *Beads: oracledb-vertexai-apxo.3*
- [ ] **Chapter 4: Schema bridge and Antigravity MCP configuration (`apex-schema-bridge`)** — implementation-ready, blocked by Ch3
  *Link: [./specs/apex-schema-bridge/](./specs/apex-schema-bridge/)* · *Beads: oracledb-vertexai-apxo.4*
- [ ] **Chapter 5: Cymbal Coffee APEX Operations Console app (`apex-ops-app`)** — implementation-ready, blocked by Ch2+Ch3+Ch4
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

## [ ] PRD: vhs-demo-recordings_20260429
*Link: [./specs/vhs-demo-recordings_20260429/](./specs/vhs-demo-recordings_20260429/)*
*Beads: not created - review gate before implementation*

## [ ] PRD: inventory
*Link: [./specs/inventory/](./specs/inventory/)*
*Beads: oracledb-vertexai-inv (active/completed chapters)*

### Chapters
- [x] **Chapter 1: Data Foundation & Fixtures (`inventory-data`)** — completed, archived locally 2026-06-23
  *Beads: oracledb-vertexai-invdata*
- [x] **Chapter 2: Deterministic Availability Routing (`inventory-grounding`)** — completed, archived locally 2026-06-23
  *Beads: oracledb-vertexai-invground*
- [ ] **Chapter 3: Inventory-Aware RAG (`inventory-rag`)**
  *Link: [./specs/inventory-rag/](./specs/inventory-rag/)*
  *Beads: oracledb-vertexai-invrag*
- [ ] **Chapter 4: Live Inventory Dashboard (`inventory-ui`)**
  *Link: [./specs/inventory-ui/](./specs/inventory-ui/)*
  *Beads: oracledb-vertexai-invui*

---

## [~] PRD: oracle-schema-annotations
*Link: [./specs/oracle-schema-annotations/](./specs/oracle-schema-annotations/)*
*Beads: pending creation*

### Chapters
- [x] **Chapter 1: DDL Annotation Contract (`schema-annotations-ddl`)**
- [x] **Chapter 2: Documentation Updates (`schema-annotations-docs`)**
- [ ] **Chapter 3: Runtime Verification (`schema-annotations-verification`)**

---


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
- `inventory-data` (`oracledb-vertexai-invdata`) and `inventory-grounding`
  (`oracledb-vertexai-invground`) completed and archived locally on
  2026-06-23 while the parent `inventory` PRD remains active for
  `inventory-rag` and `inventory-ui`. Store inventory data, deterministic
  availability routing, and coordinate/privacy guidance are synthesized in
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
