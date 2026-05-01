# Progress: Settings and Configuration Consolidation

*PRD ID: `settings-config-consolidation_20260501`*
*Status: draft for review*
*Last Updated: 2026-05-01*

## Checklist

- [x] Reviewed live settings definitions in `src/app/lib/settings.py`.
- [x] Traced production and test call sites for `get_settings()` and settings branches.
- [x] Identified settings branches with no live production reads.
- [x] Identified field-level drift between settings values and hardcoded service behavior.
- [x] Drafted consolidation recommendations and implementation chapters.
- [ ] User review accepted.
- [ ] Create Beads epic/tasks after review approval.
- [ ] Implement chapter 1: contract audit and tests.
- [ ] Implement chapter 2: core settings factory cleanup.
- [ ] Implement chapter 3: database env contract alignment.
- [ ] Implement chapter 4: AI/chat/cache consolidation.
- [ ] Implement chapter 5: web/logging cleanup.
- [ ] Implement chapter 6: docs and verification.

## Notes

- No Beads epics/tasks were created because this pass is review-gated.
- No application source files were changed by this planning pass.
- Current strong removal candidates: `ServerSettings`, `AgentSettings`,
  `CacheSettings`, unused Vertex context-cache/stream settings, unused logging
  fields, `VITE_HOT_RELOAD`, and unwired database pool timeout/recycle fields.
- Current consolidation recommendation: keep dataclasses, switch to lower-case
  immutable settings, make shell env override `.env`, and introduce a focused
  `ChatSettings` for response cache, ADK session namespace, history, and product
  RAG defaults.

