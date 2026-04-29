# Flow: UI Foundation and Routing (ui-foundation-routing_20260226)

## Specification

### Problem Summary
The current React shell and home route are scaffold-level and do not reflect the desired premium product experience. Navigation still treats `/dashboard` as primary, while the new product direction requires `/performance` as canonical.

### Confirmed Scope
- Full redesign direction is approved.
- Landing must be a modern dark mosaic with large icon tiles.
- Exactly 4 tiles on landing: Chat, Performance, and 2 placeholders.
- `/performance` becomes canonical metrics route; `/dashboard` remains compatibility path.

### Code Analysis Summary
Files reviewed for chapter planning:
- `src/js/src/routes/index.tsx`
- `src/js/src/routes/__root.tsx`
- `src/js/src/routes/chat.tsx`
- `src/js/src/routes/dashboard.tsx`
- `src/js/src/index.css`
- `docs/screenshots/cymbal_chat.png`
- `docs/screenshots/performance_dashboard.png`

Key findings:
- Home route is placeholder content and must be replaced.
- Root shell is light and generic, not aligned with target dark visual system.
- Existing `/dashboard` route is functional and can be aliased/redirected to `/performance`.
- Existing screenshots confirm the prior legacy visual language to move away from.

### Requirements
1. Replace root shell visual language with a dark minimal design baseline.
2. Replace home route with hero + 4-tile mosaic (2 active, 2 coming soon).
3. Use large icon-led cards with subtle motion and clear hierarchy.
4. Introduce `/performance` as canonical route and update navigation accordingly.
5. Preserve responsive behavior for desktop and mobile.

### Acceptance Criteria
- `/` renders redesigned dark landing with 4 tiles.
- Tile links navigate to `/chat` and `/performance`.
- Placeholder tiles are visible and clearly marked as upcoming.
- `/performance` is accessible and appears as primary metrics destination.
- `/dashboard` still resolves via compatibility behavior.

## Implementation Plan

### Phase 1: Visual Foundation
- [x] 1.1 Define dark design tokens + root shell baseline in React layout and global CSS. (`bd-5oj.1.1`)
- [x] 1.2 Ensure shell/nav hierarchy supports mobile and desktop without clutter. (`bd-5oj.1.1`)

### Phase 2: Landing Mosaic
- [x] 2.1 Replace current home route scaffold with hero section and 4-tile mosaic. (`bd-5oj.1.2`)
- [x] 2.2 Implement large icon treatment and “Coming Soon” tile states for future modules. (`bd-5oj.1.2`)

### Phase 3: Route Canon
- [x] 3.1 Add `/performance` route and adopt it as canonical in UI navigation. (`bd-5oj.1.3`)
- [x] 3.2 Implement `/dashboard` compatibility redirect/alias behavior. (`bd-5oj.1.3`)

### Phase 4: Verification
- [x] 4.1 Add/update frontend tests for landing tiles and routing behavior. (`bd-5oj.1.4`)
- [x] 4.2 Run build/test/smoke validation for route and shell stability. (`bd-5oj.1.5`)
