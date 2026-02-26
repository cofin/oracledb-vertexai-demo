# Recovery Guide: ADK Migration

This guide provides instructions for resuming the migration process.

## Current Status

**Phase 3: Framework Integration** is complete.

- The new `ADKRunner` has been integrated into the application.
- The legacy `app/services/adk` directory has been removed.

## Files Modified

- `app/services/adk/*` (new module)
- `app/services/intent.py`
- `app/services/locator.py`
- `app/server/controllers.py`
- `app/server/deps.py`
- `specs/archive/adk_legacy` (deleted)

## Next Steps

The next step is to hand off the project to the **Testing Agent** to begin **Phase 4: Verification**.

### Testing Agent Instructions

1.  The user has indicated that the test suite is currently broken.
2.  Your first task is to analyze the test failures and fix them.
3.  Once the test suite is passing, you can proceed with writing new tests for the new ADK implementation.