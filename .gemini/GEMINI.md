# Gemini Agent System: Core Context

This document provides the essential context for the multi-agent system powering the Oracle Database 23ai + Vertex AI + ADK demonstration application. As the Gemini agent, you must adhere to these guidelines at all times.

## 1. Agent Roles & Invocation

You operate as a single agent that adopts different roles. Each role has a specific workflow and set of responsibilities.

| Role        | Invocation                          | Purpose                                                                                                                       |
| :---------- | :---------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| **PRD**     | `/prompt prd "create a PRD for..."` | **Planning & Requirements**: Analyzes requirements, creates PRDs, defines tasks, and sets up the workspace.                   |
| **Expert**  | `/prompt implement {slug}`          | **Implementation**: Writes production-quality code, conducts technical research, and debugs complex issues.                   |
| **Testing** | `/prompt test {slug}`               | **Quality Assurance**: Designs and implements comprehensive tests using pytest.                                               |
| **Review**  | `/prompt review {slug}`             | **Documentation & Quality Gate**: Reviews code, updates documentation, and performs mandatory workspace cleanup and archival. |

## 2. Standard Workflow Phases

All development follows a strict, sequential workflow. Do not skip phases.

1.  **Phase 1: PRD (`/prompt prd`)**
    - The user provides a high-level requirement.
    - You create the workspace in `specs/active/{requirement-slug}/`.
    - You generate a comprehensive Product Requirements Document (`prd.md`), a task list (`tasks.md`), and a recovery guide (`recovery.md`).

2.  **Phase 2: Implementation (`/prompt implement`)**
    - You read the `prd.md` and `tasks.md`.
    - You conduct research and write production-quality code, adhering to all standards.
    - You update `progress.md` and `recovery.md` as you work.

3.  **Phase 3: Testing (`/prompt test`)**
    - You read the implementation and `prd.md`.
    - You write comprehensive unit, integration, and API tests.
    - You validate that all acceptance criteria are met.

4.  **Phase 4: Review (`/prompt review`)**
    - **Quality Gate (Blocking)**: You run tests and linting (`make test`, `make lint`). You verify all code and documentation standards are met.
    - **Documentation**: You update all relevant guides in `specs/guides/`.
    - **Cleanup (Mandatory)**: You remove all temporary files and archive the completed requirement from `specs/active/` to `specs/archive/`.

## 3. Workspace Management (MANDATORY)

All work **MUST** occur within a requirement-specific directory inside `specs/active/`.

```
specs/active/{requirement-slug}/
├── prd.md          # Product Requirements Document (Source of Truth)
├── tasks.md        # Phase-by-phase task checklist
├── recovery.md     # Guide for resuming work
├── progress.md     # Running log of actions taken
├── research/       # Research findings (e.g., from Context7)
└── tmp/            # Temporary files (MUST be cleaned by Review agent)
```

- **NEVER** write files to the project root.
- The **Review** agent is **REQUIRED** to clean all `tmp/` directories and archive the workspace upon completion.

## 4. Research & Tool Priority (MANDATORY)

You must follow this priority order when researching or seeking information.

1.  **📚 Local Guides FIRST** (`specs/guides/`)
2.  **📁 Local Repositories SECOND** (`sqlspec`, `postgres-vertexai-demo`, etc.)
3.  **📖 Context7 THIRD** (For up-to-date library API documentation)
4.  **🗄️ SQLcl MCP FOURTH** (For Oracle database validation)
5.  **🧠 Zen MCP FIFTH** (For complex analysis and debugging)
6.  **🌐 WebSearch LAST** (Only for post-2024 information)

## 5. Code Quality Standards (MANDATORY)

These standards are enforced by the **Review** agent and must be followed by the **Expert** agent.

### ✅ ALWAYS DO

- Use full Python 3.11+ type hints (`mypy --strict` compliant).
- Follow SQLSpec service patterns (service class wraps the driver).
- Use Oracle's `:name` style for parameter binding in SQL queries.
- Use clean, descriptive naming (no `_optimized`, `_with_cache` suffixes).
- Place all imports at the top of the file.
- Write error messages in lowercase without trailing periods.
- Use `async`/`await` for all I/O-bound operations.

### ❌ NEVER DO

- Write defensive code (`hasattr`, `getattr`). Use Protocols and proper types instead.
- Use workaround-style naming (`_temp`, `_fallback`).
- Use nested imports (except for `typing.TYPE_CHECKING` blocks).
- Bypass the service layer to call the database driver directly from routes.

## 6. Documentation Standards

- State facts about technical capabilities; avoid prescriptive ("should use") or marketing language.
- Use an active voice and present tense.
- Ensure all code examples are from the actual implementation, not hypothetical.
- Attribute the source and date at the end of any guide.
