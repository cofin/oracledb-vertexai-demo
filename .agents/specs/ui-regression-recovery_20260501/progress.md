# Progress: UI Regression Recovery

*PRD ID: `ui-regression-recovery_20260501`*
*Status: Draft*
*Beads epic: not created yet*

---

## Chapters

- [ ] `ui-reference-audit_20260501` - compare branch UI against `main` HTMX/Jinja templates and docs screenshots
- [ ] `chat-telemetry-recovery_20260501` - restore chat metadata, streaming polish, and grounded menu result visibility
- [ ] `explore-dashboard-recovery_20260501` - restore the five-panel explore/dashboard experience and chart quality
- [ ] `executed-sql-visibility_20260501` - expose executed SQL, bind summaries, timings, and row counts in chat/explore surfaces
- [ ] `ui-regression-verification_20260501` - lock the recovered behavior into the refactored test tree and browser screenshots

## Review Notes

- Draft aligned on 2026-05-01 after the test-suite reorganization landed.
- The reference baseline is GitHub `main`'s HTMX/Jinja UI, not the unfinished React upgrade attempt.
- All test paths in this PRD use the new `src/tests/unit/<module path>/...` and `src/tests/integration/<module path>/...` layout.
