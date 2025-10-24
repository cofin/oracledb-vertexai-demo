# Review Workflow

Invoke the Docs & Vision agent for quality gate, documentation, and MANDATORY cleanup.

## Invocation by AI Platform

- **Gemini**: `/prompt review {requirement-slug}`
- **Claude Code**: Use Task tool with subagent_type="docs-vision"
- **Codex**: `/invoke docs-vision {requirement-slug}`

## What This Does

- Validates all acceptance criteria met
- Updates documentation in specs/guides/
- Updates specs/AGENTS.md if needed
- Runs quality gate (lint, tests)
- Cleans workspace and archives requirement (MANDATORY)

## Usage Examples

### Gemini

```
/prompt review vector-search-caching
```

Or for most recent active requirement:

```
/prompt review
```

### Claude Code

```python
Task(
    subagent_type="docs-vision",
    description="Quality gate and documentation",
    prompt="Review specs/active/vector-search-caching/, document, and archive"
)
```

### Codex

```
/invoke docs-vision vector-search-caching
```

## What the Docs & Vision Agent Will Do

### Phase 1: Quality Gate ⛔ BLOCKING

1. Read PRD acceptance criteria
2. Verify all tasks complete
3. Run tests: `pytest tests/ --cov=app`
4. Run linting: `make lint` or `ruff check app/ tests/`
5. Validate standards:
   - ✅ Type hints proper
   - ✅ SQLSpec patterns followed
   - ✅ Oracle binding correct (`:name` style)
   - ✅ No defensive coding (`hasattr`, `getattr`)
   - ✅ Clean naming (no `_optimized`, `_with_cache`)
   - ✅ Top-level imports
   - ✅ Error messages lowercase, no periods
6. Check acceptance criteria:
   - ✅ Feature works with Oracle 23ai
   - ✅ Vertex AI integration functional
   - ✅ ADK agents behave correctly
   - ✅ Litestar routes work
   - ✅ Tests pass
   - ✅ Linting passes
   - ✅ Documentation complete

**If ANY criteria fail** → Request fixes from Expert/Testing → BLOCK until resolved

### Phase 2: Documentation

Only after Phase 1 passes:

1. **Update Guides** in `specs/guides/`:
   - Create or update relevant guide
   - Include code examples from actual implementation
   - Add troubleshooting section
   - Document Oracle-specific patterns
   - Explain Vertex AI integration
   - Describe ADK agent usage
   - Add performance considerations
   - Include testing examples

2. **Guide Template Structure**:
   - Overview (what and when)
   - Basic usage with code
   - Oracle-specific notes
   - Vertex AI integration
   - ADK agent patterns
   - Advanced patterns
   - Performance considerations
   - Testing
   - Troubleshooting
   - Source attribution
   - Changelog

3. **Update Standards** (if needed):
   - `specs/AGENTS.md` - If new coding standards or workflow changed

### Phase 3: Cleanup (MANDATORY)

**This is MANDATORY** - never skip cleanup:

1. **Clean tmp/ directories**:

   ```bash
   find specs/active/*/tmp -type f -delete
   ```

2. **Remove loose files**:
   - Find: `*scratch*`, `*tmp_*`, `*debug_*`, `*test_*` (not in tests/)
   - Find: Orphaned `.md`, `.sql`, `.py` files in root
   - Delete after verification

3. **Archive completed requirement**:

   ```bash
   mv specs/active/{slug} specs/archive/{slug}-$(date +%Y%m%d)
   ```

4. **Keep only last 3 active requirements**:

   ```bash
   cd specs
   ls -t active | tail -n +4 | xargs -I {} mv active/{} archive/
   ```

5. **Update archive index**:
   - Update `specs/archive/README.md` with completion note
   - Include date, summary, outcome

### Phase 4: Completion Report

Generate `specs/archive/{slug}/completion-report.md`:

```markdown
# Completion Report: {Feature Name}

**Date**: {YYYY-MM-DD}
**Status**: ✅ Complete

## Acceptance Criteria Status

- ✅ Feature works with Oracle 23ai
- ✅ Vertex AI integration functional
- ✅ ADK agents behave correctly
- ✅ Tests pass (coverage: {X}%)
- ✅ Linting passes
- ✅ Documentation complete

## Documentation

- Updated: specs/guides/{feature}.md
- Updated: specs/AGENTS.md (if applicable)

## Test Coverage

- Unit: {X}%
- Integration: {X}%
- Overall: {X}%

## Modified Files

- app/services/{service}.py
- app/db/repositories/{repo}.py
- tests/unit/test\_{service}.py
- tests/integration/test\_{integration}.py
- specs/guides/{feature}.md

## Next Steps

{What should be done next, if anything}

## Archive Location

specs/archive/{slug}-{date}/
```

## Documentation Style Standards

- **Voice**: Technical but approachable, unified voice
- **Tense**: Active voice, present tense
- **Code Examples**: From actual implementation, not hypothetical
- **Attribution**: Source and date at end
- **Changelog**: Track updates at bottom
- ❌ NO "before/after" snippets (describe current way only)
- ❌ NO prescriptive guidance ("should use", "recommended")
- ❌ NO marketing language or subjective comparisons

## After Review

Feature is complete and ready for PR/release!
