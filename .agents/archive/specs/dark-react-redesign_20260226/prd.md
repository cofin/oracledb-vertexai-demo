# Master PRD: Dark React Redesign + HTMX Retirement

## Context
The current UI is a mixed state of legacy HTMX-era expectations and scaffolded React pages. The product direction is now explicit: a full redesign to a dark, ultra-minimal, modern React experience with no HTMX dependency in the user journey. The redesign must preserve existing API behavior while upgrading visual quality, routing clarity, and extensibility.

## North Star Goal
Deliver a production-ready, dark-mode React UX where:
- `/` is a modern landing mosaic with large icon tiles.
- `/chat` is a simple but premium coffee assistant interface.
- `/performance` is the canonical performance monitoring destination.
- HTMX is retired from core product paths.

## Confirmed Product Decisions
- Scope: full redesign (no more HTMX in active UX path)
- Tile count: 4 total on landing (2 active + 2 coming soon)
- Performance route: canonical `/performance` (keep `/dashboard` compatibility)
- Visual direction: dark, ultra-minimal, hyper-modern

## Roadmap (Chapters)
1. `ui-foundation-routing_20260226`
   - Modern shell, dark design language, landing mosaic, and route canon.
2. `chat-modernization_20260226`
   - Redesign `/chat` interaction model and visual hierarchy.
3. `performance-modernization_20260226`
   - Redesign performance view at `/performance` with modern analytics presentation.
4. `htmx-retirement_20260226`
   - Remove HTMX routing/template/plugin coupling from product path.

## Global Constraints
- React-first UX; do not reintroduce HTMX dependencies into new UI flows.
- Preserve backend API contracts unless explicitly revised in a chapter.
- Maintain mobile + desktop usability.
- Keep visual language minimal: high contrast, restrained motion, generous spacing.
- All chapter task status remains Beads-driven; markdown mirrors Beads state.
