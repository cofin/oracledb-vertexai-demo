# Progress: Store-Aware Chat, Inventory, and Maps

*PRD ID: `store-location-inventory-chat_20260501`*
*Status: Accepted - tracker setup in progress*
*Last Updated: 2026-05-01*

---

## Checklist

- [x] Reviewed current chat, classifier, ADK runner, store service, frontend, and fixture structure.
- [x] Compared the current branch with the original `main` store-intent behavior.
- [x] Reviewed store and product fixtures for location, hours, and inventory data.
- [x] Checked current Google Maps URL, Maps Embed, API-key security, and browser geolocation guidance.
- [x] Rechecked 2026 Maps access docs and added separate optional Maps Embed key commands.
- [x] Added Dallas-area store fixture requirement for local/near-me testing.
- [x] Added optional scripted Maps Embed key setup requirement.
- [x] Added low-fidelity chat UI mockups for store results, optional map embed, and Dallas inventory.
- [x] Drafted full-scope PRD and implementation roadmap.
- [x] User accepted open decisions and baseline-only migration strategy.
- [x] Reviewed all existing `.agents/specs` folders for alignment.
- [x] Created chapter spec folders for implementation.
- [ ] Create Beads epic/tasks after review approval.
- [ ] Implement chapter 1: data model and fixtures.
- [ ] Implement chapter 2: store/inventory services and tools.
- [ ] Implement chapter 3: intent routing and grounded chat responses.
- [ ] Implement chapter 4: browser location and maps UI.
- [ ] Implement chapter 5: security, docs, and full verification.

---

## Notes

- Source changes remain unstarted; this pass only updates Flow planning and tracker artifacts.
- Migration strategy is resolved: modify only `0001_cymball_coffee_products.sql`; the DB will be dropped and recreated.
- Required first implementation should use Google Maps URLs because they do not require an API key.
- Embedded Google Maps should remain optional until a restricted, separate `GOOGLE_MAPS_EMBED_API_KEY` and CSP/header plan are accepted.
- The Maps key must not reuse Gemini, Vertex, or other general Google credentials.
- The implementation must add a Dallas-area store fixture and inventory rows so Dallas location prompts have a real local match.
- The implementation should add `tools/scripts/create-maps-embed-key.sh` with dry-run, restricted-key safeguards, and no tracked secret writes.
