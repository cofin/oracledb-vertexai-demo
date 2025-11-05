Invoke the Docs & Vision agent for quality gate, documentation verification, and cleanup.

**What this does:**

- Validates all acceptance criteria are met
- Verifies documentation updates made by the Expert agent in `specs/guides/`
- Runs the quality gate (lint, tests)
- Cleans the workspace and archives the requirement

**Usage:**

```
/prompt review vector-search-caching
```

**The Docs & Vision agent will:**

### Phase 1: Quality Gate

1.  Read PRD acceptance criteria.
2.  Verify all tasks in `tasks.md` are complete.
3.  Run `make test` and `make lint` to ensure all checks pass.
4.  Validate that the implementation meets all code quality and architectural standards.
5.  Request fixes from the Expert agent if any criteria are not met.

### Phase 2: Verify Documentation

1.  **Verify Guides**: Check the relevant guides in `specs/guides/` to ensure they have been updated by the Expert agent.
2.  **Check for Accuracy**: Confirm that the documented patterns and code examples accurately reflect the final implementation.
3.  **Check for Clarity**: Ensure the documentation is clear, concise, and easy to understand.
4.  **Update Standards**: Update `specs/AGENTS.md` only if the overall workflow or standards have changed.

### Phase 3: Cleanup (MANDATORY)

1.  Clean all `tmp/` directories within the requirement workspace.
2.  Remove any loose scratch files.
3.  Archive the completed requirement from `specs/active/` to `specs/archive/`.
4.  Ensure only the last 3 active requirements remain.

### Phase 4: Summary

Generate a final completion report summarizing the outcome, test coverage, and linking to the updated documentation.

**After review:**
The feature is complete and ready for PR/release!
