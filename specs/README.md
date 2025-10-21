# Universal Multi-AI Agent System

Comprehensive multi-agent workflow system for Oracle 23ai + Vertex AI + ADK development. Works with Gemini (primary), Claude Code, and Codex.

## Directory Structure

```
specs/
├── guides/              # Technical guides (COMMITTED)
│   ├── oracle-vector-search.md
│   ├── sqlspec-patterns.md
│   ├── vertex-ai-integration.md
│   ├── adk-agent-patterns.md
│   └── ... (14 guides total)
├── agents/              # Universal agent configs (COMMITTED)
│   ├── planner.md      # Planning & PRD creation
│   ├── expert.md       # Implementation specialist
│   ├── testing.md      # Test creation
│   └── docs-vision.md  # Documentation & quality gate
├── workflows/           # Universal workflows (COMMITTED)
│   ├── plan.md         # Planning workflow
│   ├── implement.md    # Implementation workflow
│   ├── test.md         # Testing workflow
│   └── review.md       # Review & documentation workflow
├── active/              # Work in progress (GITIGNORED)
│   ├── {requirement-1}/
│   ├── {requirement-2}/
│   └── {requirement-3}/
├── archive/             # Completed work (GITIGNORED)
│   └── {old-requirements}/
├── example-requirement/ # Template structure (COMMITTED)
├── AGENTS.md            # Central coordination guide (COMMITTED)
└── README.md            # This file (COMMITTED)
```

## What Gets Committed vs Gitignored

### ✅ Committed to Git

- `specs/guides/` - Technical documentation
- `specs/agents/` - Agent configurations
- `specs/workflows/` - Workflow definitions
- `specs/AGENTS.md` - Coordination guide
- `specs/example-requirement/` - Template structure
- `specs/README.md` - This documentation

### 🚫 Gitignored

- `specs/active/` - Active work (in progress)
- `specs/archive/` - Completed work
- `.gemini/` - Gemini-specific invocation layer
- `.claude/` - Claude-specific invocation layer
- `.codex/` - Codex-specific invocation layer

## Quick Start

### Using Gemini (Primary)

```bash
# Planning
/prompt plan Add real-time vector search caching

# Implementation
/prompt implement vector-search-caching

# Testing
/prompt test vector-search-caching

# Review & Documentation
/prompt review vector-search-caching
```

### Using Claude Code

```python
# Planning
Task(subagent_type="planner", description="Plan feature", prompt="Add real-time vector search caching")

# Implementation
Task(subagent_type="expert", description="Implement feature", prompt="Implement specs/active/vector-search-caching/")

# Testing
Task(subagent_type="testing", description="Create tests", prompt="Create tests for specs/active/vector-search-caching/")

# Review
Task(subagent_type="docs-vision", description="Review & document", prompt="Review specs/active/vector-search-caching/")
```

### Using Codex

```bash
# Planning
/invoke planner Add real-time vector search caching

# Implementation
/invoke expert vector-search-caching

# Testing
/invoke testing vector-search-caching

# Review
/invoke docs-vision vector-search-caching
```

## The Four Agents

### 1. Planner Agent

**Purpose**: Strategic planning, PRD creation, task breakdown

**Tools**:

- `mcp__zen__planner` - Multi-step planning
- `mcp__zen__consensus` - Multi-model decisions
- `mcp__zen__chat` - Brainstorming
- WebSearch - Research best practices

**Output**:

- Comprehensive PRD
- Phase-by-phase tasks
- Recovery guide
- Research questions

**See**: [specs/agents/planner.md](agents/planner.md)

### 2. Expert Agent

**Purpose**: Implementation with deep Oracle, Vertex AI, ADK expertise

**Tools**:

- `mcp__zen__thinkdeep` - Deep analysis
- `mcp__zen__debug` - Systematic debugging
- `mcp__zen__analyze` - Code analysis
- `mcp__context7__*` - Library documentation
- `mcp__sqlcl__*` - Oracle operations
- WebSearch - Latest updates

**Enforces**:

- ✅ Proper type hints
- ✅ SQLSpec patterns
- ✅ Oracle `:name` binding
- ✅ Clean naming
- ❌ No defensive coding
- ❌ No workaround suffixes

**See**: [specs/agents/expert.md](agents/expert.md)

### 3. Testing Agent

**Purpose**: Comprehensive test creation for pytest

**Tools**:

- `mcp__zen__debug` - Debug test failures
- `mcp__zen__chat` - Brainstorm scenarios
- WebSearch - Testing best practices

**Creates**:

- Unit tests (tests/unit/)
- Integration tests (tests/integration/)
- API tests (tests/api/)
- Edge case coverage
- Performance validation

**See**: [specs/agents/testing.md](agents/testing.md)

### 4. Docs & Vision Agent

**Purpose**: Quality gate, documentation, MANDATORY cleanup

**Phases**:

1. **Quality Gate** ⛔ BLOCKING
   - Validate all acceptance criteria
   - Run tests and linting
   - Check code standards
2. **Documentation**
   - Update specs/guides/
   - Update CLAUDE.md if needed
   - Update AGENTS.md if needed
3. **Cleanup** (MANDATORY)
   - Remove tmp/ files
   - Archive completed work
   - Keep only last 3 active specs

**See**: [specs/agents/docs-vision.md](agents/docs-vision.md)

## Workflow Phases

### Phase 1: Planning (`/prompt plan`)

**Agent**: Planner
**Output**: `specs/active/{slug}/`

1. Analyze requirement
2. Create workspace structure
3. Write comprehensive PRD
4. Break down into tasks
5. Generate recovery guide

### Phase 2: Implementation (`/prompt implement`)

**Agent**: Expert
**Input**: Reads `specs/active/{slug}/prd.md`, `tasks.md`, `research/`

1. Research patterns (specs/guides/ FIRST)
2. Use MCP tools (Context7, SQLcl, Zen)
3. Implement following standards
4. Run targeted tests
5. Update workspace

### Phase 3: Testing (`/prompt test`)

**Agent**: Testing
**Input**: Reads `specs/active/{slug}/recovery.md`, `progress.md`

1. Create unit tests
2. Create integration tests
3. Test edge cases
4. Validate coverage
5. Update workspace

### Phase 4: Review (`/prompt review`)

**Agent**: Docs & Vision
**Input**: Reads `specs/active/{slug}/prd.md`, `tasks.md`

1. Quality gate (BLOCKING)
2. Documentation
3. Cleanup (MANDATORY)
4. Archive

## Workspace Structure

Each requirement gets its own workspace in `specs/active/`:

```
specs/active/{requirement-slug}/
├── prd.md          # Product Requirements Document
├── tasks.md        # Phase-by-phase task checklist
├── recovery.md     # Recovery guide for resuming work
├── progress.md     # Running log (created by agents)
├── research/       # Expert research findings
│   └── *.md
└── tmp/            # Temporary files (cleaned by Docs & Vision)
```

## Research Priority

All agents follow this priority:

1. **📚 specs/guides/** - Local technical guides (FIRST)
2. **📁 Local repos** - sqlspec, postgres-vertexai-demo, litestar-sqlstack (SECOND)
3. **📖 Context7** - Library documentation (THIRD)
4. **🗄️ SQLcl MCP** - Oracle operations (FOURTH)
5. **🧠 Zen MCP** - Complex analysis (FIFTH)
6. **🌐 WebSearch** - 2025+ updates only (LAST)

## Tech Stack

**Backend**: Python 3.11+, Litestar, Oracle 23ai, python-oracledb, SQLSpec, Vertex AI, Google ADK
**Frontend**: Jinja2, HTMX, Tailwind CSS
**Testing**: pytest, pytest-asyncio, pytest-databases[oracle]
**Build**: uv, make
**Documentation**: Markdown

## Key Patterns

### SQLSpec Service Pattern

Services wrap SQLSpec driver for database operations:

```python
class ProductService(SQLSpecService):
    async def search(self, query: str):
        return await self.driver.select(
            "SELECT * FROM product WHERE name LIKE :query",
            query=f"%{query}%"
        )
```

### Oracle Vector Search

VECTOR(768, FLOAT32), HNSW indexes, VECTOR_DISTANCE(COSINE):

```sql
SELECT id, name,
       VECTOR_DISTANCE(embedding, :query_vec, COSINE) as similarity
FROM product
ORDER BY similarity ASC
FETCH FIRST 10 ROWS ONLY
```

### Vertex AI Integration

text-embedding-005 (768 dimensions), gemini-2.5-flash-002:

```python
embedding = await vertex_ai.embed_text(
    text="coffee products",
    task_type="RETRIEVAL_QUERY"
)
```

### ADK Tool Patterns

Tool wrappers call service classes:

```python
@tool
async def search_products(query: str, service: ProductService):
    return await service.search(query)
```

## Code Quality Standards

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

See [CLAUDE.md](../CLAUDE.md) for complete standards.

## MCP Tools Available

### Context7 (Library Documentation)

- `mcp__context7__resolve-library-id` - Find library IDs
- `mcp__context7__get-library-docs` - Get up-to-date documentation

### Zen (Analysis & Planning)

- `mcp__zen__planner` - Multi-step planning
- `mcp__zen__consensus` - Multi-model decisions
- `mcp__zen__thinkdeep` - Deep analysis
- `mcp__zen__debug` - Systematic debugging
- `mcp__zen__analyze` - Code analysis
- `mcp__zen__chat` - Brainstorming

### SQLcl (Oracle Operations)

- Execute SQL queries
- Validate Oracle syntax
- Check schema structures
- Test VECTOR_DISTANCE queries

## Documentation Standards

From `specs/AGENTS.md`:

- State facts about technical capabilities
- Avoid prescriptive guidance ("should use", "recommended")
- No marketing language or subjective comparisons
- Active voice, present tense
- Code examples from actual implementation
- Source attribution at end
- Changelog entries at bottom

## AI-Specific Invocation

While specs/ content is universal, each AI has its own invocation layer:

- **Gemini**: Uses `.gemini/prompts/` (thin wrappers pointing to specs/workflows/)
- **Claude Code**: Uses `.claude/agents/` (thin wrappers pointing to specs/agents/)
- **Codex**: Uses `.codex/commands/` (thin wrappers pointing to specs/workflows/)

All AI-specific directories are gitignored. The single source of truth is specs/.

## Gemini-First Project

This project is **Gemini-first**:

- Primary AI: Google Gemini (via `gemini` CLI or API)
- MCP tools optimized for Gemini integration
- Vertex AI native integration
- Google ADK patterns
- Compatible with Claude Code and Codex for flexibility

## Getting Help

- **Agent documentation**: See `specs/agents/{agent}.md`
- **Workflow documentation**: See `specs/workflows/{workflow}.md`
- **Technical guides**: See `specs/guides/`
- **Coordination**: See `specs/AGENTS.md`
- **Code standards**: See `CLAUDE.md`
- **Project structure**: See `AGENTS.md`

## Contributing

When adding new patterns or standards:

1. Update relevant guide in `specs/guides/`
2. Update `specs/AGENTS.md` if workflow changes
3. Update `CLAUDE.md` if code standards change
4. Ensure examples are from actual implementation
5. Add source attribution and changelog entry

---

**Source**: Universal Multi-AI Agent System v1.0
**Date**: 2025-10-20
**Primary AI**: Gemini (with Claude Code and Codex support)
