# Plan Workflow

Invoke the Planner agent to create a comprehensive requirement workspace.

## Invocation by AI Platform

- **Gemini**: `/prompt plan {requirement}`
- **Claude Code**: Use Task tool with subagent_type="planner"
- **Codex**: `/invoke planner {requirement}`

## What This Does

- Creates `specs/active/{feature-slug}/` directory structure
- Writes detailed PRD with Oracle, Vertex AI, and ADK considerations
- Creates actionable task list
- Generates recovery guide for resuming work
- Identifies research questions for Expert

## Usage Examples

### Gemini

```
/prompt plan Add vector search caching with TTL management
```

### Claude Code

```python
Task(
    subagent_type="planner",
    description="Plan vector search caching",
    prompt="Create comprehensive plan for adding vector search caching with TTL management"
)
```

### Codex

```
/invoke planner Add vector search caching with TTL management
```

## What the Planner Will Do

1. Analyze the requirement and existing codebase patterns
2. Create workspace: `specs/active/{slug}/`
3. Write comprehensive PRD covering:
   - Oracle 23ai vector search patterns
   - Vertex AI embedding integration
   - Google ADK agent implications
   - SQLSpec service layer patterns
   - Litestar + HTMX considerations
   - Testing strategy
   - Documentation requirements
4. Create task breakdown by phase
5. Write recovery guide for any agent to resume

## Output Structure

```
specs/active/{slug}/
├── prd.md          # Product Requirements Document
├── tasks.md        # Phase-by-phase task checklist
├── recovery.md     # Recovery guide for resuming work
├── progress.md     # Running log (created by agents)
├── research/       # Expert research findings
└── tmp/            # Temporary files (cleaned by Docs & Vision)
```

## After Planning

Next steps:

- **Implement**: `/prompt implement {slug}` (Gemini) or invoke Expert agent
- Review the PRD and tasks before starting implementation
- Expert agent will read all workspace files
