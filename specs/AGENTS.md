# Universal Agent Coordination Guide

Comprehensive guide for the Oracle 23ai + Vertex AI + ADK multi-AI agent system. Works with Gemini (primary), Claude Code, and Codex. Covers agent responsibilities, workflow patterns, tool usage, and workspace management.

## Agent Responsibilities Matrix

| Responsibility            | Planner      | Expert                    | Testing          | Docs & Vision       |
| ------------------------- | ------------ | ------------------------- | ---------------- | ------------------- |
| **Research**              | ✅ Primary   | ✅ Implementation details | ✅ Test patterns | ✅ Doc standards    |
| **Planning**              | ✅ Primary   | ❌                        | ❌               | ❌                  |
| **Implementation**        | ❌           | ✅ Primary                | ✅ Tests only    | ❌                  |
| **Testing**               | ❌           | ✅ Verify own code        | ✅ Primary       | ✅ Run quality gate |
| **Documentation**         | ✅ PRD/tasks | ✅ Code comments          | ✅ Test docs     | ✅ Primary          |
| **Quality Gate**          | ❌           | ❌                        | ❌               | ✅ Primary          |
| **Cleanup**               | ❌           | ❌                        | ❌               | ✅ MANDATORY        |
| **Multi-Model Consensus** | ✅ Primary   | ✅ Complex decisions      | ❌               | ❌                  |
| **Workspace Management**  | ✅ Create    | ✅ Update                 | ✅ Update        | ✅ Archive & Clean  |

## Workflow Phases

### Phase 1: Planning (`/prompt plan`)

**Agent:** Planner
**Purpose:** Research-grounded planning and workspace creation

**Steps:**

1. Research guides and use `google_web_search`
2. Create structured plan with `planner` tool
3. Get consensus on complex decisions (`consensus` tool)
4. Create workspace in `specs/active/{requirement-slug}/`
5. Write PRD, tasks, research, recovery docs

**Output:**

```
specs/active/{requirement-slug}/
├── prd.md          # Product Requirements Document
├── tasks.md        # Implementation checklist
├── research/       # Research findings
│   └── plan.md    # Detailed plan
├── tmp/            # Temporary files
└── recovery.md     # Session resume guide
```

**Hand off to:** Expert agent for implementation

### Phase 2: Implementation (`/prompt implement`)

**Agent:** Expert
**Purpose:** Write clean, production-quality code

**Steps:**

1. Read workspace (prd.md, tasks.md, research/plan.md)
2. Research implementation details (guides, Context7, SQLcl)
3. Implement following specs/AGENTS.md standards
4. Run targeted tests
5. Update workspace (tasks.md, recovery.md)

**Tools Used:**

- `debug` (systematic debugging)
- `thinkdeep` (complex decisions)
- `analyze` (code analysis)
- `chat` (brainstorming, validation)

**Output:**

- Production code in app/
- Updated workspace files

**Hand off to:** Testing agent for comprehensive tests

### Phase 3: Testing (`/prompt test`)

**Agent:** Testing
**Purpose:** Create comprehensive unit and integration tests

**Steps:**

1. Read implementation
2. Consult testing guide
3. Create unit tests (tests/unit/)
4. Create integration tests (tests/integration/)
5. Test Oracle vector search, caching, ADK agents
6. Test edge cases
7. Verify coverage
8. Update workspace

**Output:**

- Unit tests in tests/unit/
- Integration tests in tests/integration/
- API tests in tests/api/
- Updated workspace files

**Hand off to:** Docs & Vision for documentation and quality gate

### Phase 4: Review (`/prompt review`)

**Agent:** Docs & Vision
**Purpose:** Documentation, quality gate, and MANDATORY cleanup

**3 Sequential Phases:**

1. **Documentation:**
   - Update docs/guides/
   - Update specs/AGENTS.md if needed
   - Build docs locally

2. **Quality Gate (MANDATORY):**
   - Run `make lint` (must pass)
   - Run `make test` (must pass)
   - Verify PRD acceptance criteria
   - Check code quality standards
   - **BLOCKS if quality gate fails**

3. **Cleanup (MANDATORY):**
   - Remove all tmp/ directories
   - Archive requirement to specs/archive/
   - Keep only last 3 active requirements
   - Remove loose files

**Output:**

- Complete documentation
- Clean workspace
- Archived requirement
- Work ready for PR/commit

## Tool Usage

### `planner`

**Who uses:** Planner agent
**Purpose:** Structured, multi-step planning
**When:** Creating detailed implementation plans

**Example:**

```python
print(default_api.planner(
    step="Plan ADK agent integration for product recommendations",
    step_number=1,
    total_steps=6,
    next_step_required=True
))
```

### `consensus`

**Who uses:** Planner, Expert
**Purpose:** Multi-model decision verification
**When:** Complex architectural decisions, significant API changes

**Example:**

```python
print(default_api.consensus(
    step="Evaluate: Add native streaming support to chat interface",
    models=[
        {"model": "gemini-2.5-pro", "stance": "neutral"},
        {"model": "openai/gpt-5", "stance": "neutral"}
    ],
    relevant_files=["app/services/chat.py"],
    next_step_required=False
))
```

### `debug`

**Who uses:** Expert
**Purpose:** Systematic debugging workflow
**When:** Complex bugs, mysterious errors, performance issues

**Example:**

```python
print(default_api.debug(
    step="Investigate ORA-51805 vector format error",
    step_number=1,
    total_steps=5,
    hypothesis="Array binding format incorrect for Oracle VECTOR type",
    findings="Found array.array('f', embedding) pattern missing",
    confidence="high",
    next_step_required=True
))
```

### `thinkdeep`

**Who uses:** Expert
**Purpose:** Deep analysis for complex decisions
**When:** Architecture decisions, complex refactoring

**Example:**

```python
print(default_api.thinkdeep(
    step="Analyze adding RAG capabilities to ADK agents",
    step_number=1,
    total_steps=4,
    hypothesis="Can use Oracle vector search with ADK tool integration",
    findings="ADK supports custom tools, Oracle has VECTOR_DISTANCE",
    focus_areas=["architecture", "performance"],
    confidence="high",
    next_step_required=True
))
```

### `analyze`

**Who uses:** Expert, Docs & Vision
**Purpose:** Code analysis (architecture, performance, security, quality)
**When:** Code review, performance optimization, quality gate

**Example:**

```python
print(default_api.analyze(
    step="Analyze service layer for performance bottlenecks",
    step_number=1,
    total_steps=3,
    analysis_type="performance",
    findings="Found N+1 queries in product recommendations",
    confidence="high",
    next_step_required=True
))
```

### `chat`

**Who uses:** All agents
**Purpose:** Brainstorming, validation, second opinions
**When:** Need to think through a problem, validate approach

**Example:**

```python
print(default_api.chat(
    prompt="How should we handle embedding cache invalidation for product updates?",
    files=["app/services/vertex_ai.py", "app/db/repositories/cache.py"]
))
```

### `google_web_search`

**Who uses:** All agents
**Purpose:** Research current best practices (2025+)
**When:** Need recent best practices, Oracle-specific patterns

**Example:**

```python
print(default_api.google_web_search(query="Oracle 23ai HNSW index best practices 2025"))
```

## Workspace Management

### Structure

```
specs/
├── {requirement-1}/      # Active requirement
│   ├── prd.md
│   ├── tasks.md
│   ├── recovery.md
│   ├── research/
│   │   └── plan.md
│   └── tmp/              # Cleaned by Docs & Vision
├── {requirement-2}/      # Active requirement
├── {requirement-3}/      # Active requirement
├── archive/              # Completed requirements
│   └── {old-requirement}/
└── README.md
```

### Cleanup Protocol (MANDATORY)

**When:** After every `/prompt review` (Docs & Vision agent)

**Steps:**

1. Remove all tmp/ directories:

   ```bash
   find specs/*/tmp -type d -exec rm -rf {} +
   ```

2. Archive completed requirement:

   ```bash
   mv specs/{requirement} specs/archive/{requirement}
   ```

3. Keep only last 3 active requirements:

   ```bash
   # If more than 3 active, move oldest to archive
   ```

**This is MANDATORY - never skip cleanup.**

## Code Quality Standards

All agents MUST enforce these standards:

### ✅ ALWAYS DO

- **Type hints:** Proper type hints on all functions
- **SQLSpec patterns:** Service wraps SQLSpec driver
- **Oracle binding:** Use `:name` parameter binding
- **Clean naming:** No workaround suffixes (\_optimized, \_with_cache)
- **Top-level imports:** All imports at top of file (except TYPE_CHECKING)
- **Error messages:** lowercase, no periods, include context
- **Async patterns:** Use async/await consistently

### ❌ NEVER DO

- **Defensive coding:** `hasattr`, `getattr` checks
- **Workaround naming:** `_optimized`, `_with_cache`, `_fallback`
- **Nested imports:** Imports inside functions (except TYPE_CHECKING)
- **Bypass patterns:** Don't bypass service layer

## Guides Reference

All agents should consult guides before implementing:

### Core Guides

```
docs/guides/
├── oracle-vector-search.md      # Oracle 23ai vector patterns
├── sqlspec-patterns.md          # SQLSpec service patterns
├── vertex-ai-integration.md     # Vertex AI embeddings & Gemini
├── adk-agent-patterns.md        # Google ADK agent patterns
├── litestar-htmx.md             # Litestar + HTMX patterns
├── caching-strategies.md        # Oracle-backed caching
├── testing-guide.md             # pytest patterns
└── deployment.md                # Docker/Podman deployment
```

## MCP Tools Available

### Context7

- `resolve-library-id`: Find library IDs
- `get-library-docs`: Get up-to-date documentation

### Zen

- `planner`: Multi-step planning
- `consensus`: Multi-model decisions
- `debug`: Systematic debugging
- `thinkdeep`: Deep analysis
- `analyze`: Code analysis
- `chat`: Brainstorming, validation

### SQLcl (if available)

- Execute SQL queries
- Validate Oracle syntax
- Check schema structures

### WebSearch

- Research latest patterns
- Find Oracle 23ai examples
- Vertex AI best practices
