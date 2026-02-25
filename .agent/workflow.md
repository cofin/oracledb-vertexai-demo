# Workflow

## Task Management
- Select tasks using `br ready`.
- Mark as `in_progress` in Beads before starting.
- Close in Beads with commit SHA upon completion.

## Development Cycle (TDD)
1. **Red:** Write failing tests.
2. **Green:** Implement minimal code to pass tests.
3. **Refactor:** Clean up code while keeping tests green.
4. **Clean:** Remove any dead code or temporary logic.

## Documentation
- Log discoveries in `learnings.md` per flow.
- Elevate reusable patterns to `.agent/patterns.md`.

## Commits
- Commit after every task completion.
- Use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- Never commit dead code or commented-out blocks.
