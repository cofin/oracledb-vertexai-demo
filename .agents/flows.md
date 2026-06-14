# Flow Registry

This file tracks all PRDs (Product Requirements Documents) for the project. Each PRD has its own detailed plan in its respective folder.

---

## [~] PRD: adb-podman-lab-hardening
*Link: [./specs/adb-podman-lab-hardening/](./specs/adb-podman-lab-hardening/)*
*Beads: oracledb-vertexai-9p5 (master epic)*
*Research: [./research/research_adb_hooks_ux_lab/](./research/research_adb_hooks_ux_lab/)*

### Chapters
- [ ] **Chapter 1: ADB-Free vector-memory startup hardening + podman/OL runtime validation (`adb-vector-memory-hardening`)** — implementation-ready
  *Link: [./specs/adb-vector-memory-hardening/](./specs/adb-vector-memory-hardening/)*
  *Beads: oracledb-vertexai-9p5.1*
- [ ] **Chapter 2: Lab overhaul — Oracle Linux + podman + accuracy fixes (`oraclelinux-podman-lab`)** — draft, blocked by Ch1
  *Link: [./specs/oraclelinux-podman-lab/](./specs/oraclelinux-podman-lab/)*
  *Beads: oracledb-vertexai-9p5.2*
- [ ] **Chapter 3: UI UX/correctness fixes (`ui-quality-fixes`)** — draft
  *Link: [./specs/ui-quality-fixes/](./specs/ui-quality-fixes/)*
  *Beads: oracledb-vertexai-9p5.3*

---

## [ ] PRD: vhs-demo-recordings_20260429
*Link: [./specs/vhs-demo-recordings_20260429/](./specs/vhs-demo-recordings_20260429/)*
*Beads: not created - review gate before implementation*

---

## [ ] PRD: settings-config-consolidation_20260501
*Link: [./specs/settings-config-consolidation_20260501/](./specs/settings-config-consolidation_20260501/)*
*Beads: not created - review gate before implementation*

---

## [x] PRD: oracle-apex-integration
*Link: [./specs/oracle-apex-integration/](./specs/oracle-apex-integration/)*
*Beads: oracledb-vertexai-apex (closed after runtime verification)*

---

## [ ] PRD: inventory
*Link: [./specs/inventory/](./specs/inventory/)*
*Beads: oracledb-vertexai-inv (active/completed chapters)*

### Chapters
- [x] **Chapter 1: Data Foundation & Fixtures (`inventory-data`)**
  *Link: [./specs/inventory-data/](./specs/inventory-data/)*
  *Beads: oracledb-vertexai-invdata*
- [x] **Chapter 2: Deterministic Availability Routing (`inventory-grounding`)**
  *Link: [./specs/inventory-grounding/](./specs/inventory-grounding/)*
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
