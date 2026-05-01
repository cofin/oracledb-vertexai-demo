# Progress: Demo-First Source Organization

*PRD ID: `demo-source-organization_20260501`*
*Status: Planned*
*Beads epic: `oracledb-vertexai-8jt`*

---

## Chapters

- [x] `source-organization-contract_20260501` - source layout contract, audit inventory, and guard tests
- [x] `app-core-source-organization_20260501` - app config, logging, discovery, env, and fixture utilities
- [x] `domain-source-organization_20260501` - controllers, product/store services, schemas, web, and system domain pass
- [ ] `adk-runner-source-organization_20260501` - ADK runner narrative split and focused private helper modules
- [ ] `cli-tools-source-organization_20260501` - coffee CLI helpers and operational tools
- [ ] `source-organization-verification_20260501` - final whole-tree audit, patterns update, and aggregate gates

## Review Notes

- Draft created from live repository inspection on 2026-05-01.
- Beads epic created: `oracledb-vertexai-8jt`.
- Chapter Beads issues created: `oracledb-vertexai-8jt.1` through `oracledb-vertexai-8jt.6`.
- Planning-only pass: no production source files were modified.
- Shared worktree note at creation time: unrelated modified or untracked files were already present. Implementation must inspect and preserve those changes rather than reverting them.
- Chapter 1 implemented on 2026-05-01; verification passed with focused pytest, `make lint`, `make test`, and diff checks.
- Chapter 2 implemented on 2026-05-01; verification passed with focused pytest, source organization guard, `make lint`, `make test`, and diff checks.
- Chapter 3 implemented on 2026-05-01; verification passed with focused domain unit/integration tests, source organization guard, `make lint`, `make test`, and diff checks.
