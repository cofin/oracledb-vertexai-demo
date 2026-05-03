# Learnings: VHS Terminal Demo Recordings

## 2026-04-29 - User Review Revision

- **Decision:** The demo recording workflow should be live and reset-backed, not only credential-free command tours.
- **Destructive guard:** Recording must go through a script that warns the user and requires an explicit confirmation before running `make wipe-infra`.
- **Tape order:** Record separate tapes for `make start-infra`, database upgrade, load fixtures plus a no-op embedding generation/check, and server startup.
- **Verification boundary:** Do not run tests or VHS recordings during implementation. The user will run the tapes with the generated Makefile/script entrypoint.
