# Spec: Initial Setup and Legacy Guide Synthesis

## Overview

Initialize the project with the Flow methodology, synthesize existing technical documentation into the new context, and establish persistent task tracking with Beads.

## Goals

- Finalize `.agent/` scaffolding.
- Initialize Beads and create the first epic.
- Complete the migration of legacy guides into `tech-stack.md`, `product-guidelines.md`, and `patterns.md`.
- Verify project health using `manage.py doctor`.

## Implementation Plan

### Phase 1: Persistence & Scaffolding

- [x] Task: bd-3eo.1: Initialize Beads Epic for this Flow
- [x] Task: bd-3eo.2: Create Beads tasks for the implementation plan
- [x] Task: bd-3eo.3: Generate `.agent/index.md` and `knowledge/index.md`

### Phase 2: Knowledge Synthesis

- [x] Task: bd-3eo.4: Refine `tech-stack.md` with detailed service patterns
- [x] Task: bd-3eo.5: Refine `product-guidelines.md` with HTMX and reference mandates
- [x] Task: bd-3eo.6: Populate `patterns.md` with deep technical "Gotchas" from legacy guides

### Phase 3: Verification

- [x] Task: bd-3eo.7: Run `uv run manage.py doctor` and resolve any environment issues
- [ ] Task: bd-3eo.8: Flow - User Manual Verification 'Initial Setup' (Protocol in workflow.md)
