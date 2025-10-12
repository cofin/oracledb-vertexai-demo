Invoke the Planner agent to create a comprehensive requirement workspace.

**What this does:**

- Creates `.agents/{feature-slug}/` directory structure
- Writes detailed PRD with Oracle, Vertex AI, and ADK considerations
- Creates actionable task list
- Generates recovery guide for resuming work
- Identifies research questions for Expert

**Usage:**

```
/prompt plan Add vector search caching with TTL management
```

**The Planner will:**

1. Analyze the requirement and existing codebase patterns
2. Create workspace: `.agents/vector-search-caching/`
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

**Output Structure:**

```
.agents/vector-search-caching/
├── prd.md          # Product Requirements Document
├── tasks.md        # Phase-by-phase task checklist
├── recovery.md     # Recovery guide for resuming work
├── progress.md     # Running log (created by agents)
├── research/       # Expert research findings
└── tmp/            # Temporary files (cleaned by Docs & Vision)
```

**After planning, run:**

- `/prompt implement` to build the feature
- Or invoke Expert agent directly for implementation
