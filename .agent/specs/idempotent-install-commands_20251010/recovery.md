# Recovery Guide: Idempotent Installation Commands

## Current Status
**Last updated**: 2025-10-10

**Status**: Planning Complete / Ready for Implementation

**Last completed task**: Planning and task breakdown

**Next task**: Task 1.1 - Add utility functions to manage.py

## To Resume Work

1. **Read PRD**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/prd.md`
2. **Check tasks**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tasks.md`
3. **Review detailed tasks**: `/home/cody/code/g/oracledb-vertexai-demo/specs/active/idempotent-install-commands/tasks-detail.md`
4. **Understand context**: See key decisions below

## Key Decisions Made

### Decision 1: Idempotency is Default Behavior
**What**: All install commands check if tool is installed BEFORE attempting installation
**Why**: Better user experience, prevents re-downloads, reduces errors
**Impact**: Removes need for `--if-missing` flag, adds `--force` flag instead

### Decision 2: Connection Name Change
**What**: Rename default SQLcl connection from "mcp_demo" to "cymbal_coffee"
**Why**: Aligns with project branding (Cymbal Coffee demo application)
**Impact**: Requires migration logic for existing connections

### Decision 3: Cross-Configuration Always Checks
**What**: Installing SQLcl checks for Gemini CLI, installing Gemini checks for SQLcl
**Why**: Seamless integration, reduces manual configuration steps
**Impact**: MCP configuration happens automatically when both tools present

### Decision 4: MCP Configuration is Additive
**What**: Never overwrite existing MCP server configurations
**Why**: Preserve user customizations, avoid breaking existing setups
**Impact**: Re-running installers only adds missing MCP servers

### Decision 5: Utility Functions for Detection
**What**: Create reusable helper functions for tool detection and MCP checking
**Why**: DRY principle, easier testing, consistent behavior
**Impact**: ~50 LOC of new utility functions

## Blockers

**None currently** - All dependencies are in place, ready for implementation.

## Files to Modify

### Primary Implementation
- **`/home/cody/code/g/oracledb-vertexai-demo/manage.py`**
  - Lines 242+: Add utility functions (is_tool_installed, is_mcp_server_configured, etc.)
  - Lines 243-313: Update configure_sqlcl_connection_with_password() for new connection name
  - Lines 316-366: Update configure_gemini_mcp_sqlcl() to check if already configured
  - Lines 369-452: Update configure_gemini_mcp_extensions() to skip configured extensions
  - Lines 744-831: Make install_uv() idempotent
  - Lines 834-939: Make install_sqlcl() idempotent with connection name parameter
  - Lines 941-1070: Make install_gemini_cli() idempotent with MCP re-configuration
  - Lines 1073-1164: Make install_mcp_toolbox() idempotent

### Makefile Updates
- **`/home/cody/code/g/oracledb-vertexai-demo/Makefile`**
  - Lines 41-45: Make install-uv target idempotent
  - Lines 35-39: Make install-sqlcl target idempotent

### Documentation Updates
- **`/home/cody/code/g/oracledb-vertexai-demo/docs/guides/gemini-mcp-integration.md`**
  - Line 108-109: Change mcp_demo to cymbal_coffee
  - Line 361: Change mcp_demo to cymbal_coffee
  - Add migration section after line 361

## Research Outputs

**None required** - All patterns already established in codebase:
- Tool detection: `shutil.which()` pattern at lines 769, 860, 962, 1096
- Version checking: `run_command([tool, "--version"])` pattern throughout
- JSON manipulation: Gemini settings.json pattern at lines 333-366
- SQLcl connection management: Pattern at lines 243-313

## Implementation Strategy

### Phase 1: Foundation (30 minutes)
- Add utility functions (Task 1.1-1.4)
- Test utility functions with existing tools

### Phase 2: Core Idempotency (90 minutes)
- Make UV installation idempotent (Task 2)
- Make SQLcl installation idempotent (Task 3)
- Make Gemini CLI installation idempotent (Task 4)
- Make MCP Toolbox installation idempotent (Task 5)

### Phase 3: Improvements (45 minutes)
- Update MCP configuration functions (Task 6)
- Update connection name references (Task 7)

### Phase 4: Validation (90 minutes)
- Run all test scenarios (Task 8)
- Update documentation (Task 9)
- Final validation and cleanup (Task 10)

### Total Estimated Time: 4-6 hours

## Quick Start Commands

**To begin implementation**:

```bash
# Navigate to project
cd /home/cody/code/g/oracledb-vertexai-demo

# Create a feature branch (recommended)
git checkout -b feature/idempotent-install

# Open manage.py in editor
# Start with Task 1.1: Add is_tool_installed() function after line 242

# Test as you go
python manage.py install uv
python manage.py install uv  # Should skip second time
```

## Testing Strategy

**Incremental testing approach**:

1. After adding utility functions → Test with existing tools
2. After each installer update → Test install/re-install/force
3. After cross-configuration → Test both directions
4. After migration logic → Test with old connection name
5. Final → Run all test scripts in tmp/ directory

**Test files location**: `specs/active/idempotent-install-commands/tmp/test-*.sh`

## Success Criteria

Implementation is complete when:

- [ ] All 4 installers (UV, SQLcl, Gemini CLI, MCP Toolbox) are idempotent
- [ ] Re-running any installer skips gracefully with informative message
- [ ] --force flag works for all installers
- [ ] Cross-configuration works in both directions (SQLcl ↔ Gemini)
- [ ] Connection name is "cymbal_coffee" by default
- [ ] Migration from "mcp_demo" works automatically
- [ ] MCP configuration never overwrites existing servers
- [ ] All test scenarios pass
- [ ] Documentation is updated and accurate
- [ ] Makefile targets are idempotent

## Rollback Plan

If issues arise during implementation:

1. **Git**: Use feature branch, can discard changes with `git checkout main`
2. **Backup**: No configuration files are deleted, only modified
3. **Test Environment**: Test in clean environment before committing
4. **Incremental**: Commit after each major task completes

## Notes

- This is a **medium complexity** task (4-6 hours)
- **No breaking changes** to external APIs or behavior
- **Backward compatible** with existing installations
- **User-facing improvement** - better UX for installation commands
- **Low risk** - mainly defensive programming and better UX messages
