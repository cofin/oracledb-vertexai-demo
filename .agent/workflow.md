# Project Workflow

## Guiding Principles

1. **Beads is the Source of Truth:** Task status lives in Beads (`br ready`, `br close`). Use `/flow:sync` to export Beads state to spec.md when needed.
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation
3. **Test-Driven Development:** Write unit tests before implementing functionality
4. **High Code Coverage:** Aim for >80% code coverage for all modules
5. **User Experience First:** Every decision should prioritize user experience
6. **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## Beads Integration

Beads provides persistent cross-session memory. Initialized in stealth mode during setup.

### Session Protocol

**Session Start:**

```bash
br status                          # Workspace overview
br ready                           # List unblocked tasks (dependency-aware)
br list --status in_progress       # Resume active work
```

**Session End:**

```bash
br sync --flush-only         # Sync notes locally
git add .beads/
git commit -m "sync beads"
```

> If `br` is unavailable, workflow degrades gracefully to git-only tracking.

### When to Track in Beads

**Rule: If work takes >5 minutes, track it in Beads.**

| Duration | Action | Example |
|----------|--------|---------|
| <5 min | Just do it | Fix typo, update config |
| 5-30 min | Create task | Add validation, write test |
| 30+ min | Create task with subtasks | Implement feature |

**Why this matters:**

- Notes survive context compaction - critical for multi-session work
- `br ready` finds unblocked work automatically
- If resuming in 2 weeks would be hard without context, use Beads

### Creating Issues with Full Context

**CRITICAL: Always include `--description` with `br create`, then add notes via `br update`:**

```bash
br create "Task name" --parent {epic_id} -p 2 \
  --description="WHY this issue exists and WHAT needs to be done"

# Then add context notes (br create does NOT support --notes):
br update {id} --notes "CONTEXT: files affected, dependencies, origin command, timestamp"
```

- `--description`: Purpose and goal (set at creation with `br create`)
- `--notes`: Context for future agents (set via `br update` — survives compaction!)
- Priority levels: P0=critical, P1=high, P2=medium, P3=low, P4=backlog

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow (Beads-First)

**CRITICAL:** Beads is the source of truth. Never write `[x]`, `[~]`, `[!]`, or `[-]` markers to spec.md. After ANY Beads state change, agents MUST run `/flow:sync` to update spec.md.

1. **Select Task:** Use `br ready` for dependency-aware selection, or fall back to parsing spec.md

2. **Mark In Progress:**
   - Sync to Beads: `br update <id> --status in_progress`
   - **Do NOT edit spec.md** - Beads is source of truth

3. **Write Failing Tests (Red Phase):**
   - Create a new test file for the feature or bug fix.
   - Write one or more unit tests that clearly define the expected behavior and acceptance criteria for the task.
   - **CRITICAL:** Run the tests and confirm that they fail as expected. This is the "Red" phase of TDD. Do not proceed until you have failing tests.

4. **Implement to Pass Tests (Green Phase):**
   - Write the minimum amount of application code necessary to make the failing tests pass.
   - Run the test suite again and confirm that all tests now pass. This is the "Green" phase.

5. **Refactor (Optional but Recommended):**
   - With the safety of passing tests, refactor the implementation code and the test code to improve clarity, remove duplication, and enhance performance without changing the external behavior.
   - Rerun tests to ensure they still pass after refactoring.

6. **Verify Coverage:** Run coverage reports using the project's chosen tools. For example, in a Python project, this might look like:
   ```bash
   pytest --cov=app --cov-report=html
   ```
   Target: >80% coverage for new code. The specific tools and commands will vary by language and framework.

7. **Document Deviations:** If implementation differs from tech stack:
   - **STOP** implementation
   - Update `tech-stack.md` with new design
   - Add dated note explaining the change
   - Resume implementation

8. **Commit Code Changes:**
   - **CRITICAL:** Based on project configuration, commits are performed at the **end of each phase**, not after individual tasks.
   - Stage all code changes related to the tasks completed in the current phase.
   - Propose a clear, concise commit message covering the phase's work.
   - Perform the commit.

9. **Record Task Completion (Beads-First):**
   - **Step 9.1: Get Commit Hash:** Obtain the hash of the commit that covers this work (note: commits happen at phase-end).
   - **Step 9.2: Close in Beads:** `br close <id> --reason "commit: <sha>"`
   - **Step 9.3 (MANDATORY):** Run `/flow:sync <flow_id>` to export Beads state to spec.md.
   - **Step 9.4 (Git Notes):** Use Git Notes ONLY when absolutely necessary for persistent, non-commit metadata.
   - **Do NOT manually edit spec.md markers** - use `/flow:sync` instead

10. **Log Learnings:**
    - Append discoveries to track's `learnings.md`
    - Sync to Beads: `br update <id> --notes "pattern: ..."`
    - Elevate reusable patterns to `.agent/patterns.md` at phase completion

### Knowledge Flywheel (Three-Tier)

1. **Capture** - After each task, append learnings to track's `learnings.md`
2. **Elevate** - At phase/track completion, move reusable patterns to `.agent/patterns.md`
3. **Extract** - At archive, persist full learnings to `knowledge/{flow_id}.md`
4. **Inherit** - New flows read `patterns.md` + scan `knowledge/index.md`

**Three-Tier Knowledge:**

| Tier | File | Loaded | Purpose |
|------|------|--------|---------|
| **Patterns** | `.agent/patterns.md` | Always | Elevated actionable rules for priming |
| **Knowledge Index** | `.agent/knowledge/index.md` | Always | Lightweight scan of all flow learnings |
| **Knowledge Entries** | `.agent/knowledge/{flow_id}.md` | On demand | Full detailed learnings per flow |

**Important:** `.agent/patterns.md` is NOT archived with tracks. It remains at the top level as persistent project knowledge. Knowledge entries in `.agent/knowledge/` also persist independently of archives.

**Learnings Entry Format:**

```markdown
## [YYYY-MM-DD HH:MM] - Phase N Task M: Task Description

- **Implemented:** Brief description
- **Files changed:** path/to/files
- **Commit:** abc1234
- **Learnings:**
  - Patterns: Codebase uses X for Y
  - Gotchas: Must do Z before W
  - Context: Module A owns B
```

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `spec.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**
    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in this phase, you must first find the starting point. Read `spec.md` to find the Git commit SHA of the *previous* phase's checkpoint. If no previous checkpoint exists, the scope is all changes since the first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only <previous_checkpoint_sha> HEAD` to get a precise list of all files modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files (e.g., `.json`, `.md`, `.yaml`).
        -   For each remaining code file, verify a corresponding test file exists.
        -   If a test file is missing, you **must** create one. Before writing the test, **first, analyze other test files in the repository to determine the correct naming convention and testing style.** The new tests **must** validate the functionality described in this phase's tasks (`spec.md`).

3.  **Execute Automated Tests with Proactive Debugging:**
    -   Before execution, you **must** announce the exact shell command you will use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to verify the phase. **Command:** `CI=true npm test`"
    -   Execute the announced command.
    -   If tests fail, you **must** inform the user and begin debugging. You may attempt to propose a fix a **maximum of two times**. If the tests still fail after your second proposed fix, you **must stop**, report the persistent failure, and ask the user for guidance.

4.  **Propose a Detailed, Actionable Manual Verification Plan:**
    -   **CRITICAL:** To generate the plan, first analyze `product.md`, `product-guidelines.md`, and `spec.md` to determine the user-facing goals of the completed phase.
    -   You **must** generate a step-by-step plan that walks the user through the verification process, including any necessary commands and specific, expected outcomes.
    -   The plan you present to the user **must** follow this format:

        **For a Frontend Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Start the development server with the command:** `npm run dev`
        2.  **Open your browser to:** `http://localhost:3000`
        3.  **Confirm that you see:** The new user profile page, with the user's name and email displayed correctly.
        ```

        **For a Backend Change:**
        ```
        The automated tests have passed. For manual verification, please follow these steps:

        **Manual Verification Steps:**
        1.  **Ensure the server is running.**
        2.  **Execute the following command in your terminal:** `curl -X POST http://localhost:8080/api/v1/users -d '{"name": "test"}'`
        3.  **Confirm that you receive:** A JSON response with a status of `201 Created`.
        ```

5.  **Await Explicit User Feedback:**
    -   After presenting the detailed plan, ask the user for confirmation: "**Does this meet your expectations? Please confirm with yes or provide feedback on what needs to be changed.**"
    -   **PAUSE** and await the user's response. Do not proceed without an explicit yes or confirmation.

6.  **Create Checkpoint Commit:**
    -   Stage all changes. If no changes occurred in this step, proceed with an empty commit.
    -   Perform the commit with a clear and concise message (e.g., `flow(checkpoint): Checkpoint end of Phase X`).

7.  **Record Verification in Beads:**
    -   Update the epic with verification summary: `br comments add <epic_id> "Phase N verified: tests passed, manual verification confirmed by user, checkpoint: <sha>"`

8.  **Sync to spec.md (MANDATORY):**
    -   Run `/flow:sync <flow_id>` to export current Beads state to spec.md for human-readable status
    -   **Do NOT manually edit spec.md** - Beads is source of truth

9.  **Announce Completion:** Inform the user that the phase is complete and the checkpoint has been recorded in Beads.

### Quality Gates

Before marking any task complete, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80%)
- [ ] Code follows project's code style guidelines (as defined in `code-styleguides/`)
- [ ] All public functions/methods are documented (e.g., docstrings, JSDoc, GoDoc)
- [ ] Type safety is enforced (e.g., type hints, TypeScript types, Go types)
- [ ] No linting or static analysis errors (using the project's configured tools)
- [ ] Works correctly on mobile (if applicable)
- [ ] Documentation updated if needed
- [ ] No security vulnerabilities introduced

## Development Commands

**AI AGENT INSTRUCTION: This section should be adapted to the project's specific language, framework, and build tools.**

### Setup
```bash
# Example: Commands to set up the development environment (e.g., install dependencies, configure database)
# e.g., for a Node.js project: npm install
# e.g., for a Go project: go mod tidy
```

### Daily Development
```bash
# Example: Commands for common daily tasks (e.g., start dev server, run tests, lint, format)
# e.g., for a Node.js project: npm run dev, npm test, npm run lint
# e.g., for a Go project: go run main.go, go test ./..., go fmt ./...
```

### Before Committing
```bash
# Example: Commands to run all pre-commit checks (e.g., format, lint, type check, run tests)
# e.g., for a Node.js project: npm run check
# e.g., for a Go project: make check (if a Makefile exists)
```

## Testing Requirements

### Unit Testing
- Every module must have corresponding tests.
- Use appropriate test setup/teardown mechanisms (e.g., fixtures, beforeEach/afterEach).
- Mock external dependencies.
- Test both success and failure cases.

### Integration Testing
- Test complete user flows
- Verify database transactions
- Test authentication and authorization
- Check form submissions

### Mobile Testing
- Test on actual iPhone when possible
- Use Safari developer tools
- Test touch interactions
- Verify responsive layouts
- Check performance on 3G/4G

## Code Review Process

### Self-Review Checklist
Before requesting review:

1. **Functionality**
   - Feature works as specified
   - Edge cases handled
   - Error messages are user-friendly

2. **Code Quality**
   - Follows style guide
   - DRY principle applied
   - Clear variable/function names
   - Appropriate comments

3. **Testing**
   - Unit tests comprehensive
   - Integration tests pass
   - Coverage adequate (>80%)

4. **Security**
   - No hardcoded secrets
   - Input validation present
   - SQL injection prevented
   - XSS protection in place

5. **Performance**
   - Database queries optimized
   - Images optimized
   - Caching implemented where needed

6. **Mobile Experience**
   - Touch targets adequate (44x44px)
   - Text readable without zooming
   - Performance acceptable on mobile
   - Interactions feel native

## Commit Guidelines

### Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat(auth): Add remember me functionality"
git commit -m "fix(posts): Correct excerpt generation for short posts"
git commit -m "test(comments): Add tests for emoji reaction limits"
git commit -m "style(mobile): Improve button touch targets"
```

## Definition of Done

A task is complete when:

1. All code implemented to specification
2. Unit tests written and passing
3. Code coverage meets project requirements
4. Documentation complete (if applicable)
5. Code passes all configured linting and static analysis checks
6. Works beautifully on mobile (if applicable)
7. Implementation notes added to `spec.md`
8. Changes committed with proper message
9. Task closed in Beads with commit reference: `br close <id> --reason "commit: <sha>"`
10. Markdown synced via `/flow:sync` (MANDATORY after any Beads state change)

## Emergency Procedures

### Critical Bug in Production
1. Create hotfix branch from main
2. Write failing test for bug
3. Implement minimal fix
4. Test thoroughly including mobile
5. Deploy immediately
6. Document in spec.md

### Data Loss
1. Stop all write operations
2. Restore from latest backup
3. Verify data integrity
4. Document incident
5. Update backup procedures

### Security Breach
1. Rotate all secrets immediately
2. Review access logs
3. Patch vulnerability
4. Notify affected users (if any)
5. Document and update security procedures

## Deployment Workflow

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] Mobile testing complete
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Backup created

### Deployment Steps
1. Merge feature branch to main
2. Tag release with version
3. Push to deployment service
4. Run database migrations
5. Verify deployment
6. Test critical paths
7. Monitor for errors

### Post-Deployment
1. Monitor analytics
2. Check error logs
3. Gather user feedback
4. Plan next iteration

## Continuous Improvement

- Review workflow weekly
- Update based on pain points
- Document lessons learned
- Optimize for user happiness
- Keep things simple and maintainable
