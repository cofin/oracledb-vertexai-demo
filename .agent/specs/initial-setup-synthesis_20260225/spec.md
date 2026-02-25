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

- [ ] Task: Initialize Beads Epic for this Flow
- [ ] Task: Create Beads tasks for the implementation plan
- [ ] Task: Generate `.agent/index.md` and `knowledge/index.md`

### Phase 2: Knowledge Synthesis

- [ ] Task: Refine `tech-stack.md` with detailed service patterns
- [ ] Task: Refine `product-guidelines.md` with HTMX and reference mandates
- [ ] Task: Populate `patterns.md` with deep technical "Gotchas" from legacy guides

### Phase 3: Verification

- [ ] Task: Run `uv run manage.py doctor` and resolve any environment issues
- [ ] Task: Flow - User Manual Verification 'Initial Setup' (Protocol in workflow.md)
