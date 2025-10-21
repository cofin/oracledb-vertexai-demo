# Implement Workflow

Invoke the Expert agent to implement features following Oracle 23ai, Vertex AI, and ADK patterns.

## Invocation by AI Platform

- **Gemini**: `/prompt implement {requirement-slug}`
- **Claude Code**: Use Task tool with subagent_type="expert"
- **Codex**: `/invoke expert {requirement-slug}`

## What This Does

- Reads PRD and tasks from `specs/active/{slug}/`
- Researches implementation patterns
- Implements feature with quality standards
- Uses MCP tools (Context7, SQLcl, Zen)
- Updates workspace files

## Usage Examples

### Gemini

```
/prompt implement vector-search-caching
```

### Claude Code

```python
Task(
    subagent_type="expert",
    description="Implement vector search caching",
    prompt="Implement the feature in specs/active/vector-search-caching/ following all standards"
)
```

### Codex

```
/invoke expert vector-search-caching
```

## What the Expert Will Do

1. **Read workspace** - prd.md, tasks.md, research/plan.md
2. **Research implementation details**:
   - Consult specs/guides/ (FIRST)
   - Use Context7 for library docs (THIRD)
   - Use SQLcl for Oracle validation (FOURTH)
   - Use Zen MCP for complex decisions (FIFTH)
3. **Implement following standards**:
   - ✅ Proper type hints
   - ✅ SQLSpec patterns (service wraps driver)
   - ✅ Oracle binding (`:name` style)
   - ✅ Clean naming (no `_optimized` suffixes)
   - ✅ Top-level imports
   - ✅ Async patterns
4. **Run targeted tests**
5. **Update workspace** - tasks.md, recovery.md, progress.md

## Tool Priority

The Expert follows this research priority:

1. **📚 specs/guides/** - Local guides (FIRST)
2. **📁 Local repos** - sqlspec, postgres-vertexai-demo, litestar-sqlstack (SECOND)
3. **📖 Context7** - Library documentation (THIRD)
4. **🗄️ SQLcl** - Oracle operations (FOURTH)
5. **🧠 Zen MCP** - Complex analysis (FIFTH)
6. **🌐 WebSearch** - 2025+ updates only (LAST)

## Code Quality Enforced

### ✅ ALWAYS DO

- Proper type hints on all functions
- SQLSpec patterns: Service wraps driver
- Oracle binding: Use `:name` parameter binding
- Clean naming: No workaround suffixes
- Top-level imports (except TYPE_CHECKING)
- Error messages: lowercase, no periods
- Async patterns: Use async/await consistently

### ❌ NEVER DO

- Defensive coding: `hasattr`, `getattr` checks
- Workaround naming: `_optimized`, `_with_cache`, `_fallback`
- Nested imports (except TYPE_CHECKING)
- Bypass patterns: Don't bypass service layer

## After Implementation

Next steps:

- **Test**: `/prompt test {slug}` (Gemini) or invoke Testing agent
- Expert will hand off to Testing agent
- Tests must pass before documentation
