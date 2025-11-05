# PRD Workflow

Invoke the PRD agent to create a comprehensive requirement workspace.

## Invocation by AI Platform

- **Gemini**: `/prompt prd "create a PRD for..."`

## What This Does

- Creates `specs/active/{feature-slug}/` directory structure.
- Writes a detailed PRD with Oracle, Vertex AI, and ADK considerations.
- Creates an actionable task list.
- Generates a recovery guide for resuming work.
- Identifies research questions for the Expert agent.

## Usage Example

### Gemini

```
/prompt prd "create a PRD for vector search caching with TTL management"
```

## What the PRD Agent Will Do

1.  Analyze the requirement and existing codebase patterns.
2.  Create the workspace: `specs/active/{slug}/`.
3.  Write a comprehensive PRD, a task breakdown, and a recovery guide.
4.  Identify research questions for the next phase.

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

- **Implement**: `/prompt implement {slug}` (Gemini) or invoke Expert agent.
- The Expert agent will read all workspace files to begin implementation.
