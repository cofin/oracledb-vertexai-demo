# Gemini CLI Agent System

This directory configures the Gemini CLI for agent-based workflows in the Oracle Database 23ai + Vertex AI + ADK demonstration application.

## Directory Structure

```
.gemini/
├── GEMINI.md              # Main context file (auto-loaded by Gemini CLI)
├── README.md              # This file
├── prompts/               # Custom Gemini CLI commands
│   ├── plan.md           # Invoke Planner agent
│   ├── implement.md      # Invoke Expert agent
│   ├── test.md           # Invoke Testing agent
│   └── review.md         # Invoke Docs & Vision agent
└── agents/                # Agent role documentation
    ├── planner.md        # Planning specialist
    ├── expert.md         # Implementation expert
    ├── testing.md        # Testing specialist
    └── docs-vision.md    # Documentation & quality gate
```

## How Gemini CLI Works

### Context Loading

The `GEMINI.md` file is automatically loaded by Gemini CLI as persistent context for every session. It provides:

- Agent responsibilities matrix
- Workflow phases
- Tool usage guidelines
- Workspace management rules
- Code quality standards
- Guides reference

### Custom Prompts

Custom prompts in `.gemini/prompts/` are invoked using `/prompt {name}`:

```bash
# Planning phase
/prompt plan Add vector search caching with TTL management

# Implementation phase
/prompt implement vector-search-caching

# Testing phase
/prompt test vector-search-caching

# Review and documentation phase
/prompt review vector-search-caching
```

### Agent Roles

While Gemini CLI doesn't have formal "agents" like Claude Code, the prompts invoke specialized workflows:

1. **Planner** (`/prompt plan`) - Creates comprehensive PRDs, task breakdowns, workspace structure
2. **Expert** (`/prompt implement`) - Implements features using MCP tools (Context7, SQLcl, Zen)
3. **Testing** (`/prompt test`) - Writes comprehensive test suites
4. **Docs & Vision** (`/prompt review`) - Quality gate, documentation, cleanup (MANDATORY)

## Workflow Example

```bash
# 1. Start with planning
gemini
> /prompt plan Add product recommendation caching

# 2. Implement the feature
> /prompt implement product-recommendation-caching

# 3. Create tests
> /prompt test product-recommendation-caching

# 4. Review, document, and clean up
> /prompt review product-recommendation-caching
```

## MCP Tools Integration

The Gemini CLI has access to powerful MCP tools:

### Context7 (Library Documentation)

```python
# Resolve library name to Context7 ID
mcp__context7__resolve_library_id(libraryName="python-oracledb")

# Get documentation
mcp__context7__get_library_docs(
    context7CompatibleLibraryID="/oracle/python-oracledb",
    topic="vector data types"
)
```

### Zen MCP (Analysis & Planning)

- `planner` - Multi-step planning workflow
- `consensus` - Multi-model decision verification
- `thinkdeep` - Deep analysis for complex decisions
- `debug` - Systematic debugging workflow
- `analyze` - Code analysis (architecture, performance, quality)
- `chat` - Brainstorming and validation

### SQLcl MCP (Oracle Operations)

- Execute SQL queries
- Validate Oracle syntax
- Check schema structures
- Test VECTOR_DISTANCE queries

### Web Search

- Research latest patterns and best practices
- Find Oracle 23ai examples
- Vertex AI updates

## Configuration

### Settings Location

User settings: `~/.gemini/settings.json`
Project settings: `.gemini/settings.json` (not checked in)

### Example Settings

```json
{
  "contextFileName": "GEMINI.md",
  "mcpServers": {
    "context7": {
      "command": "context7-server",
      "args": []
    },
    "zen": {
      "command": "zen-mcp-server",
      "args": []
    }
  },
  "telemetry": {
    "enabled": false
  }
}
```

## Workspace Management

All work happens in `specs/{requirement-slug}/`:

```
specs/vector-search-caching/
├── prd.md              # Product Requirements Document
├── tasks.md            # Task checklist
├── recovery.md         # How to resume work
├── progress.md         # Running progress log
├── research/           # Research findings
│   └── oracle-patterns.md
└── tmp/                # Temporary files (cleaned by review)
```

### Cleanup Rules (MANDATORY)

The Docs & Vision agent (`/prompt review`) MUST:

1. Remove all `tmp/` directories
2. Remove loose scratch files
3. Archive completed requirement to `specs/archive/`
4. Keep only last 3 active requirements
5. Update archive index

## Agent Coordination

Agents communicate through workspace files:

- **Planner** creates workspace and writes PRD
- **Expert** reads PRD, implements, updates progress
- **Testing** reads implementation, writes tests, updates progress
- **Docs & Vision** validates everything, documents, archives

## Documentation Standards

From `GEMINI.md`:

- State facts about technical capabilities
- Avoid prescriptive guidance ("should use", "recommended")
- No marketing language or subjective comparisons
- Active voice, present tense
- Code examples from actual implementation
- Source attribution at end

## Research Priority

1. **📚 Local Guides FIRST** - `docs/guides/`
2. **📁 Local Repositories SECOND** - sqlspec, postgres-vertexai-demo, litestar-sqlstack
3. **🤖 Zen MCP THIRD** - Complex planning and analysis
4. **📖 Context7 FOURTH** - Library documentation
5. **🌐 WebSearch LAST** - Only for 2025+ updates

## Code Quality Standards

From `CLAUDE.md` (enforced by all agents):

### ✅ ALWAYS DO

- Proper type hints
- SQLSpec service patterns
- Oracle `:name` binding
- Clean naming (no workaround suffixes)
- Top-level imports
- Lowercase error messages
- Async patterns

### ❌ NEVER DO

- Defensive coding (`hasattr`, `getattr`)
- Workaround naming (`_optimized`, `_with_cache`)
- Nested imports (except TYPE_CHECKING)
- Bypass service layer

## Comparison: Gemini CLI vs Claude Code

| Feature           | Gemini CLI         | Claude Code                        |
| ----------------- | ------------------ | ---------------------------------- |
| Context file      | `GEMINI.md`        | `AGENTS.md`                        |
| Custom commands   | `.gemini/prompts/` | `.claude/commands/`                |
| Agent definitions | Prompts + docs     | `.claude/agents/` with frontmatter |
| Invocation        | `/prompt {name}`   | `/{name}`                          |
| MCP support       | ✅ Yes             | ✅ Yes                             |
| Workspace         | `specs/`           | `specs/`                           |

## Getting Started

1. **Install Gemini CLI**:

   ```bash
   npm install -g @google/gemini-cli
   ```

2. **Configure authentication**:

   ```bash
   export GOOGLE_API_KEY="your-api-key"
   # or use Google Cloud credentials
   ```

3. **Start a session**:

   ```bash
   gemini
   ```

4. **Use custom prompts**:
   ```bash
   > /prompt plan Add feature XYZ
   ```

## Learn More

- **Gemini CLI Docs**: https://geminicli.dev
- **MCP Protocol**: https://modelcontextprotocol.io
- **Project Guides**: `../docs/guides/`
- **Project Standards**: `../CLAUDE.md`, `../AGENTS.md`

---

**Note**: This setup mirrors the `.claude/` structure for cross-compatibility. Both Claude Code and Gemini CLI can work with this project using their respective configurations.
