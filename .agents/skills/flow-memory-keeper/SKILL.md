---
name: flow-memory-keeper
description: Use at task, phase, flow, sync, archive, finish, revise, or failure checkpoints to keep Flow specs clean, capture learnings and failures, elevate durable patterns, and refine this skill with project-specific nuances
---

# Flow Memory Keeper

## Purpose

This project-local skill prevents Flow work from drifting into stale specs, missing learnings, or archive-only knowledge.

Use it whenever work is completed, paused, blocked, revised, synced, or archived.

<workflow>

## Mandatory Outcomes

Before claiming a task, phase, or flow is complete:

1. Ensure `spec.md` is readable and current through the normal Flow sync process.
2. Capture concrete learnings in the flow's `learnings.md`.
3. Capture failures, false starts, blockers, and recovery notes when they would help a future session.
4. If the user had to repeat a correction or showed frustration that something was forgotten, flag that as a workflow gap and capture it explicitly.
5. Elevate durable patterns to `.agents/patterns.md`.
6. Update `.agents/knowledge/` chapters when the current-state knowledge base changed.
7. If the flow is complete, archive only after durable knowledge is synthesized into tracked active docs, corresponding research is moved to the archive folder, and the active spec area is uncluttered.
8. Capture validated repo-native commands and verification workflows in `.agents/workflow.md` when they were discovered or corrected during the work.

## Completion Protocol

### Task or Phase Completion

1. Append a concise entry to `.agents/specs/<flow_id>/learnings.md`:
   - what changed
   - why it changed
   - files touched
   - commands or checks that mattered
   - canonical repo commands that future agents should reuse
   - gotchas, failures, and recoveries worth remembering
   - any repeated user correction or frustration that revealed a missing default, checklist item, or workflow rule
2. Move reusable guidance into `.agents/patterns.md`.
3. If the work changed architecture, conventions, tooling, operational behavior, or canonical project commands, update the relevant `.agents/knowledge/*.md` chapter and `.agents/workflow.md`.
4. Promote repeated user corrections or frustration into an obvious durable rule instead of leaving it as a one-off note.
5. Run the normal Flow sync step so `spec.md` reflects the latest state.

### Failure Capture

Capture failure notes whenever one of these happened:

- a hypothesis was wrong
- a command or tool failed in a non-obvious way
- a host integration behaved differently than expected
- a backend migration exposed a hidden assumption
- a repeated reminder from the user revealed a workflow gap
- the user seemed frustrated that something obvious was forgotten again

Failure notes belong in `learnings.md`, but keep them short and reusable. Focus on what future agents should avoid or check earlier.

### Flow Archive

When a flow is finished:

1. Confirm the final sync/export step ran.
2. Ensure `learnings.md` is not missing critical discoveries.
3. Elevate the stable patterns and current-state knowledge before archiving.
4. Remove active links into `.agents/archive/`; readers must be able to recover durable guidance from `.agents/knowledge/`, `.agents/patterns.md`, and `.agents/workflow.md`.
5. Move or remove the flow folder (along with any associated `.agents/research/research_<flow_id>` folder, which should be placed inside the archived flow folder as `research/`) according to the Flow archive workflow, treating `.agents/archive/` as ignored disposable history.
6. Remove or avoid leaving stale scratch files in the active specs area.

</workflow>

<guardrails>

## Skill Refinement Loop

This skill should improve over time.

When you discover a repeated project nuance, add or revise a short rule below instead of keeping the lesson only in session memory.

Only keep:

- durable project-specific rules
- recurring host quirks
- recurring workflow misses
- validated project-native command wrappers that should become defaults
- user corrections or frustration that clearly indicate a missing default or checklist item
- archive/sync/learnings habits that proved necessary

Do not keep:

- one-off narrative history
- temporary debugging logs
- duplicate rules already captured elsewhere

</guardrails>

<validation>

Before claiming a task, phase, or flow is complete, verify:

- [ ] `spec.md` was synced through the normal Flow process
- [ ] `learnings.md` captures the durable lessons, failures, and recoveries
- [ ] reusable guidance was elevated to `.agents/patterns.md` when appropriate
- [ ] `.agents/knowledge/` reflects current-state knowledge when it changed
- [ ] repeated user corrections or frustration were promoted into an explicit rule when applicable
- [ ] canonical repo commands and verification flows were captured when they were learned or corrected
- [ ] completed flows are archived or removed (with their research folders moved into the archive) without leaving stale active-spec or research clutter
- [ ] no active guide, index, or workflow instruction requires a link into `.agents/archive/`

</validation>

## Project Nuances

- Add short, durable project-specific reminders here as they are discovered.
- Treat Flow sync/status as a Flow skill workflow backed by Beads state and
  `.agents/` docs; do not assume a `flow sync` shell subcommand exists.
- Treat `.agents/archive/` as ignored disposable history. Before adding or
  moving archive material, synthesize durable lessons into `.agents/knowledge/`
  and `.agents/patterns.md`, then remove active links to archive paths.
- This repo's Beads database enforces the `oracledb-vertexai-` issue ID prefix.
  When recreating missing local Flow records with explicit IDs, use that prefix
  and attach hierarchy after creation with `bd update <id> --parent <parent>`;
  `bd create --id ... --parent ...` is rejected by this Beads version.
- Inventory UI selectors must be data-driven from `StoreService`/fixtures, not
  hardcoded store preset arrays. Treat user pushback on fixed location lists as
  a workflow correction that belongs in `.agents/patterns.md`.
