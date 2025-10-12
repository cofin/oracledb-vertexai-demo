Invoke the Docs & Vision agent for quality gate, documentation, and cleanup.

**What this does:**

- Validates all acceptance criteria met
- Updates documentation in docs/guides/
- Updates CLAUDE.md and AGENTS.md if needed
- Runs quality gate (lint, tests)
- Cleans workspace and archives requirement

**Usage:**

```
/prompt review vector-search-caching
```

**Or for current active requirement:**

```
/prompt review
```

**The Docs & Vision agent will:**

### Phase 1: Quality Gate

1. Read PRD acceptance criteria
2. Verify all tasks complete
3. Check test results
4. Validate:
   - ✅ Feature works with Oracle 23ai
   - ✅ Vertex AI integration functional
   - ✅ ADK agents behave correctly
   - ✅ Litestar routes work
   - ✅ Tests pass (`make test`)
   - ✅ Linting passes (`make lint`)
   - ✅ Type hints proper
   - ✅ SQLSpec patterns followed
   - ✅ No defensive coding
5. Request fixes if criteria not met

### Phase 2: Documentation

1. Update guides in `docs/guides/`:
   - Overview and when to use
   - Basic usage with code examples
   - Oracle-specific notes
   - Vertex AI integration
   - ADK agent patterns
   - Performance considerations
   - Testing examples
   - Troubleshooting
2. Update CLAUDE.md if standards changed
3. Update AGENTS.md if workflows changed
4. Add source attribution
5. Update changelog at bottom of guide

### Phase 3: Cleanup (MANDATORY)

1. Clean tmp/ directories:
   ```bash
   find .agents/{slug}/tmp -type f -delete
   ```
2. Remove loose files:
   - Find scratch files: `*scratch*`, `*tmp_*`, `*debug_*`
   - Find orphaned test files not in `tests/`
   - Find loose `.md` and `.sql` files
3. Archive completed requirement:
   ```bash
   mv .agents/{slug} .agents/archive/
   ```
4. Keep only last 3 active requirements
5. Update .agents/README.md with completion note

### Phase 4: Summary

Generate completion report with:

- ✅ Acceptance criteria status
- 📚 Documentation links
- 🧪 Test coverage statistics
- 📦 Modified files
- 🎯 Next steps

**Documentation Style:**

- Unified voice: Technical but approachable
- Active voice, present tense
- Code examples from actual implementation
- Source attribution at end
- Changelog entries at bottom
- NO "before/after" snippets (describe current way only)

**After review:**
Feature is complete and ready for PR/release!
