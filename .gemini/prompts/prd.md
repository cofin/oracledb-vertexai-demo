# PRD Agent: Create Requirement Workspace

Invoke the PRD agent to analyze a requirement and create a comprehensive workspace for development. The magic word is `"create a PRD for..."`.

**What this does:**

- Creates the `specs/active/{feature-slug}/` directory structure.
- Writes a detailed Product Requirements Document (`prd.md`).
- Creates an actionable, phase-based task list (`tasks.md`).
- Generates a recovery guide for resuming work (`recovery.md`).
- Identifies initial research questions for the Expert agent.

**Usage:**

```
/prompt prd "create a PRD for vector search caching with TTL management"
```

**The PRD agent will:**

1.  Analyze the requirement based on the context in `.gemini/GEMINI.md`.
2.  Create the complete workspace structure.
3.  Generate all initial planning documents.

**Output Structure:**

```
specs/active/{feature-slug}/
├── prd.md          # Product Requirements Document
├── tasks.md        # Phase-by-phase task checklist
├── recovery.md     # Recovery guide for resuming work
├── progress.md     # Running log (created by agents)
├── research/       # Expert research findings
└── tmp/            # Temporary files (cleaned by Review agent)
```

**After planning, the next step is implementation:**

- `/prompt implement {feature-slug}`
