# Alignment Review: Store-Aware Chat, Inventory, and Maps

*Reviewed: 2026-05-01*
*Scope: all current folders under `.agents/specs`*

---

## Summary

The store-location PRD is a follow-on PRD, not a replacement for the Cymbal Coffee reset. It builds on the completed ADK 2 runner, named SQL extraction, HTMX/Vite frontend, and test-suite reorganization work.

Implementation must follow these alignment constraints:

- Modify only `src/app/db/migrations/0001_cymball_coffee_products.sql` for schema changes. The local database will be dropped and recreated.
- Keep all new SQL in named SQL files under `src/app/db/sql/`.
- Keep tests in the refactored `src/tests/unit/<module path>/` and `src/tests/integration/<module path>/` layout.
- Use store cards and no-key Google Maps URLs as the required map experience.
- Keep embedded maps optional behind `MAPS_ENABLE_EMBED` and `GOOGLE_MAPS_EMBED_API_KEY`.
- Preserve the current HTMX/Jinja/Vite UI direction. Do not add React or a new SPA.

---

## Existing Spec Audit

| Spec | Status | Alignment result |
|---|---|---|
| `cymbal-coffee-reset_20260429` | planned/open saga | Updated to name this PRD as a follow-on and to preserve fixture lifecycle commands needed by store/inventory work. |
| `foundation-bump_20260429` | completed | Compatible. It already established 0001-as-baseline and fixture regeneration patterns. New work must edit only 0001 and reload from scratch. |
| Domain-service restructure chapter | completed | Compatible. Store/inventory work must extend `stores.sql` and add `inventory.sql`; no inline service SQL. |
| `adk2-runner_20260429` | completed | Compatible. Store intents become new deterministic routes on the existing classifier-first runner. |
| `htmx-vite-frontend_20260429` | completed | Compatible. Maps UI belongs in the existing chat template and `src/resources/main.js`. |
| `prune-and-document_20260429` | in progress | Updated to clarify that this PRD is a separate follow-on and should not prune fixture/export or store docs paths that it depends on. |
| `documentation-setup` | ready/open | Compatible. Future docs should include store/maps only after this PRD lands. |
| `vector-calculator_20260429` | planned/open | Compatible. Both touch frontend educational surfaces, but vector calculator is Explore-only and store maps are chat-only. |
| `ui-regression-recovery_20260501` | implemented/closed in Beads | Metadata/progress updated to match closed tracker state. Store maps build on the recovered chat shell. |
| `test-suite-reorganization_20260501` | implemented/closed | Compatible. New tests must use the strict module-path layout it established. |
| `vhs-demo-recordings_20260429` | review | Compatible. Future tapes can add Dallas/store/map prompts after this PRD lands; not required for initial VHS scope. |
| `pyapp-packaging_20260429` | planning | Compatible. Maps key script must not bake secrets into PyApp artifacts. |
| `pyapp-enablement_20260429` | planned | Compatible. Optional maps embed settings remain runtime env/config, not packaged secrets. |
| `release-automation_20260429` | planned | Compatible. Release automation must not publish maps keys. |
| `ruff-copyright-modernization` | in progress | Compatible. Any new script from this PRD needs the repo copyright/SPDX header convention. |
| `store-location-inventory-chat_20260501` | accepted/planned | This PRD now owns the store, browser-location, inventory, maps, and Dallas fixture scope. |

---

## Sequencing

Recommended implementation order:

1. Finish any currently active UI/docs cleanup that is already in progress if it touches the same chat template.
2. Implement `store-data-foundation_20260501`.
3. Implement `store-query-services_20260501`.
4. Implement `store-intent-routing_20260501`.
5. Implement `browser-location-maps-ui_20260501`.
6. Implement `store-maps-security-docs_20260501`.

The first three store chapters are backend/data work and can be reviewed before browser geolocation or Maps Embed is introduced.
