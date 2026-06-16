# Flow: ui-quality-fixes

*Chapter 3 of PRD `adb-podman-lab-hardening` (Beads epic `oracledb-vertexai-9p5.3`)*
*Source: `.agents/research/research_adb_hooks_ux_lab/research.md` (Part 2)*

## Specification

Fix accessibility/correctness defects in the chat + explore UI and remove verified dead code. Scope: High + Med + verified cleanup. Cross-check both sides (template + JS) before each change; preserve coordinate-privacy and no-key Maps behavior. SSE event names (`delta`/`final`/`error`) and camelCase payloads are already consistent — do not change them.

## Code Analysis Summary

- `src/resources/main.js:151-173` — `renderSqlPhase`; undefined classes at `:155-157`.
- `src/resources/main.js:264-306` — `showTelemetryPopover` (`root.hidden=false` at `:274`, Close button at `:281`); `hideTelemetryPopover` at `:308-`.
- `src/resources/main.js:820-850` — `appendPendingText`/`setPendingText`/`finalizePendingReply`; `handleChatStreamEvent` `:868-888` (final branch `:874-880`).
- `src/resources/main.js:89-112` — `renderMetrics` (the live metrics path).
- `pages/chat.html.j2:48` (`#messages aria-live="polite"`), `:104` (popover root `aria-hidden="true"`); `pages/explore.html.j2:243` (popover root), `:121-144` (dup presets), `:69-70` (trend fallback).
- `src/resources/styles.css:316-319` — mobile `.ui-panel` width override.

## Implementation Plan

### Phase 1: High — telemetry popover a11y (`9p5.3.1`)
- [ ] 1.1 In `showTelemetryPopover` (`main.js:264-306`), `root.removeAttribute("aria-hidden")` when showing; in `hideTelemetryPopover` (`:308-`), `root.setAttribute("aria-hidden","true")` with `root.hidden=true`.
- [ ] 1.2 Apply to both `pages/chat.html.j2:104` and `pages/explore.html.j2:243` roots; optionally add `role="dialog"` + focus the Close button (`:281`).

### Phase 2: High — style SQL bind rows (`9p5.3.2`)
- [ ] 2.1 Replace `help-tooltip-metric*` (`main.js:155-157`) with existing utilities (`flex items-center justify-between gap-2 text-xs`, label `text-muted`, value `font-mono text-strong`) or define the classes in `styles.css`. Keep `escapeHtml`.

### Phase 3: Med — mobile grid overflow (`9p5.3.3`)
- [ ] 3.1 Scope `styles.css:316-319` so `.ui-panel { width: calc(100vw - 2rem) }` no longer applies to chat-grid panel children (exclude the chat shell or target standalone panels only).

### Phase 4: Med — aria-live streaming (`9p5.3.4`)
- [ ] 4.1 Set the streaming subtree to `aria-live="off"` (or remove from `#messages`, `chat.html.j2:48`); add a visually-hidden `aria-live="polite"` region updated once with the final answer in the `final` branch (`main.js:874-880`).

### Phase 5: Verified cleanup (`9p5.3.5`)
- [ ] 5.1 Confirm nothing posts to `/api/chat` (non-stream HTML path). If dead, remove `partials/_chat_response.html.j2`, `partials/_metrics_badges.html.j2` (OOB), and the `message.html.j2` metrics footer.
- [ ] 5.2 Remove the duplicate explore preset (`explore.html.j2:121-144`) or differentiate by format.
- [ ] 5.3 Render trend text only when `trend_value` is present (`explore.html.j2:69-70`). Optionally drop unused `data-*` hooks.

### Verification Gate
- [ ] Popover content + Close button reachable when open; streaming announces once; no 375px horizontal overflow.
- [ ] `make lint`/`make test` green; visual smoke of `/` and `/explore`.
- [ ] Update Beads task states and reconcile the markdown view.
