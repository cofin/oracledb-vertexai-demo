# Tasks for Idempotent Installation Commands

## High-Level Checklist

- [ ] 1. Add Utility Functions
  - [ ] Add `is_tool_installed()` helper
  - [ ] Add `is_mcp_server_configured()` helper
  - [ ] Add `is_sqlcl_connection_saved()` helper
  - [ ] Add `migrate_sqlcl_connection()` helper

- [ ] 2. Make UV Installation Idempotent
  - [ ] Modify `install_uv()` to check before installing
  - [ ] Update Makefile `install-uv` target
  - [ ] Test UV re-installation behavior

- [ ] 3. Make SQLcl Installation Idempotent
  - [ ] Modify `install_sqlcl()` to check before installing
  - [ ] Add `--connection-name` parameter
  - [ ] Implement connection migration logic
  - [ ] Update Makefile `install-sqlcl` target
  - [ ] Test SQLcl re-installation behavior

- [ ] 4. Make Gemini CLI Installation Idempotent
  - [ ] Modify `install_gemini_cli()` to check before installing
  - [ ] Add MCP re-configuration for existing installs
  - [ ] Test Gemini CLI re-installation behavior

- [ ] 5. Make MCP Toolbox Installation Idempotent
  - [ ] Modify `install_mcp_toolbox()` to check before installing
  - [ ] Test MCP Toolbox re-installation behavior

- [ ] 6. Improve MCP Configuration Functions
  - [ ] Update `configure_gemini_mcp_sqlcl()` to skip if configured
  - [ ] Update `configure_sqlcl_connection_with_password()` to use new connection name
  - [ ] Update `configure_gemini_mcp_extensions()` to skip configured extensions

- [ ] 7. Update Connection Name References
  - [ ] Change default from "mcp_demo" to "cymbal_coffee" in manage.py
  - [ ] Update docs/guides/gemini-mcp-integration.md examples
  - [ ] Add migration logic for existing "mcp_demo" connections

- [ ] 8. Testing
  - [ ] Test fresh installation flow
  - [ ] Test re-installation (should skip)
  - [ ] Test cross-configuration (SQLcl → Gemini)
  - [ ] Test cross-configuration (Gemini → SQLcl)
  - [ ] Test connection migration
  - [ ] Test --force flag behavior

- [ ] 9. Documentation
  - [ ] Update install command docstrings
  - [ ] Update gemini-mcp-integration.md guide
  - [ ] Add migration notes for "mcp_demo" → "cymbal_coffee"
  - [ ] Document idempotency behavior

- [ ] 10. Validation & Cleanup
  - [ ] Verify all installers are idempotent
  - [ ] Verify cross-configuration works both directions
  - [ ] Verify connection name change is transparent
  - [ ] Run through all test scenarios
