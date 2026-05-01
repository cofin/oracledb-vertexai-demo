# Progress: UI Regression Recovery

*PRD ID: `ui-regression-recovery_20260501`*
*Status: Active*
*Beads epic: `oracledb-vertexai-4d6.8`*

---

## Chapters

- [ ] `ui-reference-audit_20260501` - compare branch UI against `main` HTMX/Jinja templates and docs screenshots
- [ ] `chat-telemetry-recovery_20260501` - restore chat metadata, streaming polish, and grounded menu result visibility
- [ ] `explore-dashboard-recovery_20260501` - restore the four-panel explore/dashboard experience and chart quality
- [ ] `executed-sql-visibility_20260501` - expose executed SQL, bind summaries, timings, and row counts in chat/explore surfaces
- [ ] `ui-regression-verification_20260501` - lock the recovered behavior into the refactored test tree and browser screenshots

## Review Notes

- Draft aligned on 2026-05-01 after the test-suite reorganization landed.
- The reference baseline is GitHub `main`'s HTMX/Jinja UI, not the unfinished React upgrade attempt.
- All test paths in this PRD use the new `src/tests/unit/<module path>/...` and `src/tests/integration/<module path>/...` layout.
- Current user-facing Oracle label is `Oracle 26ai`; do not restore older `Oracle 23ai` copy when recovering UI from screenshots.
- Phase 3 restored the Explore query prefill and real HTMX form posting to `/api/vector-demo`; classify-compare was later descoped and removed from the active UI/API surface.
- Phase 4 restored the Explore analytics panel with ApexCharts for response trends, vector search performance, and system breakdown on a typed chart payload.
- Phase 5 removed classify-compare, refreshed screenshots, tightened desktop layouts, and fixed `/explore?q=...` so vector search and EXPLAIN PLAN run on load with clean inline unavailable states when local Vertex/Oracle configuration is missing.
