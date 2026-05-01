# Flow: Browser Location and Maps UI (browser-location-maps-ui_20260501)

*Chapter 4 of [store-location-inventory-chat_20260501](../store-location-inventory-chat_20260501/prd.md)*
*Beads: `oracledb-vertexai-f6u.4`*

---

## Objective

Render store-aware chat results in the current HTMX/Jinja frontend with explicit browser-location opt-in, no-key Google Maps URL actions, and optional single-map embed support.

---

## Dependencies

- Requires `store-intent-routing_20260501`.
- Builds on `ui-regression-recovery_20260501` and the recovered chat shell.

---

## Scope

### Browser Location

- Add a user-click "Use my location" control.
- Call `navigator.geolocation.getCurrentPosition()` only after user action.
- Use:
  - `enableHighAccuracy: false`
  - `timeout: 8000`
  - `maximumAge: 300000`
- Keep coordinates in memory for the page session.
- Submit location context only after opt-in.
- Handle grant, denial, timeout, and unsupported states.
- Offer city/zip fallback.

### Chat Rendering

Render store and inventory results from structured payload fields:

- store card
- hours summary
- phone/address
- distance if present
- inventory status if present
- Directions/Open in Google Maps action

The UI must match the PRD mockup behavior:

- store cards first
- one optional selected map panel
- no page-load geolocation prompt

### Maps

Required:

- Google Maps URLs for search/directions.
- Works without a Google Maps API key.

Optional:

- Single selected-store Maps Embed iframe only when `MAPS_ENABLE_EMBED=true` and `GOOGLE_MAPS_EMBED_API_KEY` is configured.
- Fallback to links when disabled or missing.

---

## Tests

- Frontend tests in `src/tests/unit/src/resources/test_chat_frontend.py`.
- Integration tests for chat final payload rendering fields.
- Browser/manual smoke for desktop and mobile widths if Playwright exists in the repo.

---

## Acceptance Criteria

- Browser never prompts for location on page load.
- Location opt-in handles grant, denial, timeout, and unsupported states.
- Dallas prompt renders a Dallas store card.
- Directions/Open in Google Maps works with no key.
- Embedded map does not render unless explicitly configured.
- Only one iframe can be open at a time.
- UI remains compact and consistent with the recovered chat design.
