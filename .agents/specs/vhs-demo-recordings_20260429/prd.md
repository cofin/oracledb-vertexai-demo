# Master PRD: VHS Terminal Demo Recordings

*PRD ID: `vhs-demo-recordings_20260429`*
*Created: 2026-04-29*
*Status: Draft for user review - planning only*

---

## North Star

Add reproducible terminal-demo GIFs to `oracledb-vertexai-demo` using VHS tapes, following the proven Litestar ecosystem pattern from `sqlspec` and `litestar-vite`.

The end state is a small, explicit Makefile workflow that records `docs/_tapes/*.tape` into `docs/_static/demos/*.gif`, keeps the recordings deterministic, and lets contributors regenerate demos locally without learning VHS details.

No source behavior changes are part of this PRD.

---

## Reviewed Sources

### `~/code/litestar/sqlspec`

- Tapes live in `docs/_tapes/`: `quickstart.tape`, `query_builder.tape`, `migration_workflow.tape`.
- GIF output paths are declared inside each tape as `docs/_static/demos/<name>.gif`.
- `Makefile:274-291` defines `docs-demos` and `docs-all`.
- `CONTRIBUTING.rst:66-104` documents VHS, `ffmpeg`, `ttyd`, standard tape header, and `make docs-demos`.

Important implementation notes:

- Good pattern: standard VHS header uses `Catppuccin Mocha`, font size 14, 1000x600 dimensions, padding 20, and hidden setup steps.
- Risk to avoid: `docs-demos` exits 0 when `vhs` is missing, masks per-tape failures with `|| true`, and sets `VHS_NO_SANDBOX=true;` without exporting it to the `vhs` child process.
- Current local output directory contains only `.gitkeep`, so the referenced GIFs are not present in this checkout.

### `~/code/litestar/litestar-vite`

- Tapes live in `docs/_tapes/`: `scaffolding.tape`, `hmr.tape`, `type-generation.tape`, `assets-cli.tape`, `production-build.tape`.
- GIF output paths are declared inside each tape as `docs/_static/demos/<name>.gif`.
- `Makefile:280-292` defines `docs-demos` and `docs-all`.
- `CONTRIBUTING.rst:82-125` documents VHS requirements, install commands, `make docs-demos`, and available demos.

Important implementation notes:

- Good pattern: `docs-demos` fails fast when VHS is missing and prefixes each recording with `VHS_NO_SANDBOX=true vhs "$$tape"`.
- Good pattern: generated GIFs are present in `docs/_static/demos/`, so docs render without requiring contributors to generate assets first.
- Risk to handle: the loop assumes at least one tape exists; a robust target should detect an empty `docs/_tapes/` directory clearly.

### Current repo

- No `docs/_tapes/` directory exists yet.
- Existing docs assets are static screenshots under `docs/screenshots/`.
- The root `Makefile` has no docs or demo recording targets yet.
- `.agents/specs/documentation-setup/prd.md` already plans Sphinx docs and `make docs`, `make docs-serve`, `make docs-clean`.
- Local host currently has the external VHS toolchain installed: `vhs v0.11.0`, `ffmpeg 6.1.1`, `ttyd 1.7.4`.

---

## Product Decisions

1. Use the Litestar ecosystem convention:
   - input: `docs/_tapes/*.tape`
   - output: `docs/_static/demos/*.gif`
   - live destructive command: `make docs-demos-live`
2. Commit generated GIFs, matching `litestar-vite`, so README/Sphinx pages render on GitHub without requiring VHS.
3. The live recording workflow is intentionally destructive for local demo infrastructure. It must be prompt-gated by a script before it runs `make wipe-infra`.
4. The implementation agent must not run tests and must not run the VHS tapes. The user will run the recording script locally.
5. Do not make `make docs` depend on VHS. VHS is an external Go/native toolchain and should stay opt-in.
6. Do not make `docs-all` depend on the destructive live recording target. A future non-destructive `docs-demos` target may be wired into `docs-all`, but `docs-demos-live` stays manually invoked.
7. Make demo recording fail when prerequisites are missing or a tape fails. Recording failures are content failures, not warnings.
8. Keep tape setup hidden and deterministic. Tapes should assume the repo is already installed, then show only commands useful to a reader.

---

## Roadmap

### Chapter 1 - `vhs-demo-foundation_20260429`

Set up the demo recording asset structure and contributor documentation.

Deliverables:

- Create `docs/_tapes/`.
- Create `docs/_static/demos/` with `.gitkeep` if no GIF is generated yet.
- Add a short VHS section to `CONTRIBUTING.md` or the future Sphinx contributor page.
- Document prerequisites: `vhs`, `ffmpeg`, and `ttyd`.
- Document install hints:
  - Linux with Go: `go install github.com/charmbracelet/vhs@latest`
  - macOS: `brew install vhs`
- Document the standard tape header:

```text
Set Shell "bash"
Set FontSize 14
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 50ms
```

Acceptance:

- A contributor can identify where to add tapes and where generated GIFs land.
- The docs say `make docs-demos-live` is the canonical live regeneration command and warn that it resets local infra after confirmation.
- No app source files are changed.

### Chapter 2 - `vhs-recording-script_20260429`

Add a prompt-gated script and root Makefile target for the live recording sequence.

Deliverables:

- Create `tools/scripts/record-vhs-demos.sh`.
- Add a Makefile target that delegates to the script:

```makefile
.PHONY: docs-demos-live
docs-demos-live: ## Record live terminal demo GIFs from VHS tapes; resets local infra after prompt
	@./tools/scripts/record-vhs-demos.sh
```

- Optionally keep a non-destructive `docs-demos` target later for tapes that do not touch infrastructure.

Recommended script behavior:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "This will destroy and recreate the local Oracle demo environment."
echo "It will run: make wipe-infra, then record the VHS demo sequence."
printf "Type DESTROY DEMO ENV to continue: "
read -r confirmation

if [[ "${confirmation}" != "DESTROY DEMO ENV" ]]; then
  echo "Aborted."
  exit 1
fi

for cmd in vhs ffmpeg ttyd; do
  command -v "${cmd}" >/dev/null 2>&1 || {
    echo "${cmd} is required for VHS demos"
    exit 1
  }
done

mkdir -p docs/_static/demos

make wipe-infra

for tape in \
  docs/_tapes/01-start-infra.tape \
  docs/_tapes/02-upgrade.tape \
  docs/_tapes/03-load-fixtures-and-embed-check.tape \
  docs/_tapes/04-run-server.tape
do
  VHS_NO_SANDBOX=true vhs "${tape}"
done
```

Optional generic Makefile surface for future non-destructive tapes:

```makefile
.PHONY: docs-demos
docs-demos: ## Generate terminal demo GIFs from VHS tapes
	@set -euo pipefail; \
	for cmd in vhs ffmpeg ttyd; do \
		command -v "$$cmd" >/dev/null 2>&1 || { \
			echo "${ERROR} $$cmd is required for VHS demos"; \
			exit 1; \
		}; \
	done; \
	mkdir -p docs/_static/demos; \
	shopt -s nullglob; \
	tapes=(docs/_tapes/*.tape); \
	if [ "$${#tapes[@]}" -eq 0 ]; then \
		echo "${WARN} No VHS tapes found in docs/_tapes"; \
		exit 0; \
	fi; \
	for tape in "$${tapes[@]}"; do \
		echo "${INFO} Recording $$tape..."; \
		VHS_NO_SANDBOX=true vhs "$$tape"; \
	done; \
	echo "${OK} Demo GIFs generated"

.PHONY: docs-demos-clean
docs-demos-clean: ## Remove generated terminal demo GIFs
	@rm -f docs/_static/demos/*.gif
	@echo "${OK} Demo GIFs removed"
```

Optional target after `make docs` exists, only if a non-destructive `docs-demos` target is added:

```makefile
.PHONY: docs-all
docs-all: docs-demos docs ## Generate demos then build documentation
```

Acceptance:

- `make docs-demos-live` prompts before destroying local infra and refuses to proceed without the exact confirmation phrase.
- `tools/scripts/record-vhs-demos.sh` runs `make wipe-infra` before recording the first tape.
- `make docs-demos-live` fails if `vhs`, `ffmpeg`, or `ttyd` is missing.
- `make docs-demos-live` fails if any tape fails.
- `VHS_NO_SANDBOX=true` is passed to each `vhs` process, not just assigned in the shell.
- `make docs-demos-clean` removes generated GIFs without touching screenshots or other docs assets.
- The implementation agent does not run `make docs-demos-live`, `vhs`, or tests; the user runs the tapes.

### Chapter 3 - `vhs-initial-tapes_20260429`

Create the live reset-backed terminal demo sequence.

Required tape set:

1. `docs/_tapes/01-start-infra.tape`
   - Output: `docs/_static/demos/01-start-infra.gif`
   - Records `make start-infra`.
   - Purpose: show local Oracle 23ai infrastructure starting from a clean reset.

2. `docs/_tapes/02-upgrade.tape`
   - Output: `docs/_static/demos/02-upgrade.gif`
   - Records the canonical database upgrade command.
   - Current repo command: `make migrate`, which wraps `uv run python manage.py database upgrade`.
   - Purpose: show schema upgrade after infrastructure is online.

3. `docs/_tapes/03-load-fixtures-and-embed-check.tape`
   - Output: `docs/_static/demos/03-load-fixtures-and-embed-check.gif`
   - Records `make load-fixtures`.
   - Then runs a read-only embedding readiness check so it shows that fixture-loaded embeddings leave no work to do.
   - Do not rely on `uv run coffee bulk-embed`; Ch 5 removes that maintainer-only command from the canonical CLI. Prefer a small SQL/count check or the future `tools/dev/regen_embeddings.py --check` once Ch 5 lands.
   - Purpose: demonstrate that loading fixtures gives a ready dataset without paying the full embedding-generation cost during the recording.

4. `docs/_tapes/04-run-server.tape`
   - Output: `docs/_static/demos/04-run-server.gif`
   - Records `make run`.
   - Stops the server with `Ctrl+C` after the startup line is visible.
   - Purpose: show the final local app startup step.

Acceptance:

- Every tape includes hidden setup for `.venv` activation and any directory prep.
- The reset happens in `tools/scripts/record-vhs-demos.sh`, not inside each tape.
- Tapes run in sequence and rely on state from prior tapes: reset -> start infra -> upgrade -> load fixtures and no-op embedding check -> run server.
- The fixture/embedding tape must not generate a full embedding set during recording. It should show the embedding command finding no work after fixtures are loaded.
- GIFs are committed under `docs/_static/demos/`.
- The README or Sphinx docs reference the generated GIFs.
- The implementation handoff tells the user to run `make docs-demos-live`; it does not run the tapes for them.

### Chapter 4 - `vhs-docs-integration_20260429`

Wire the demos into whichever docs surface is active after review.

If Sphinx docs are already implemented:

- Add a "Terminal Demos" page or section.
- Use `.. image:: /_static/demos/<name>.gif` for generated GIFs.
- Do not wire `docs-demos-live` into `docs-all`; it is destructive and remains manually invoked.

If Sphinx docs are not implemented yet:

- Reference the GIFs from `README.md` using relative Markdown image links.
- Leave `docs-all` unchanged unless a separate non-destructive `docs-demos` target exists.

Acceptance:

- GitHub-rendered docs show committed GIFs without requiring VHS.
- Local contributors regenerate demos with `make docs-demos-live` after accepting the destructive prompt.
- `make docs` remains a Sphinx-only command and does not require VHS.

---

## Global Constraints

- Planning-only until user approval: do not modify Makefile, docs, README, or tape files before review.
- Keep implementation scoped to documentation/demo assets and Makefile commands.
- Do not change application runtime behavior, database schema, API routes, or frontend code for this PRD.
- Do not introduce a Python dependency for VHS. VHS is an external CLI prerequisite.
- Do not run tests as part of this work unless the user explicitly changes that instruction.
- Do not run the VHS tapes as part of this work; the user owns tape execution.
- Generated GIFs are source assets for docs and should be tracked unless the reviewer explicitly chooses local-only recordings.
- Use ASCII filenames with lowercase kebab-case tape names.
- Destructive local infra reset is allowed only through the prompt-gated recording script.

---

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| VHS recordings are flaky because commands depend on local Oracle state. | Use a single prompt-gated script that resets once, then records tapes in dependency order. |
| The recording script destroys local infrastructure unexpectedly. | Require exact typed confirmation before `make wipe-infra`; do not run the script automatically from docs or tests. |
| Generated GIFs bloat the repo. | Start with four concise GIFs; keep terminal dimensions at 1000x600; review file sizes before committing. |
| Live demo recording breaks clean dev machines. | Keep VHS and infra reset out of `make docs`, `make lint`, and `make test`; require it only for `make docs-demos-live`. |
| Tape failures get hidden. | Use `set -euo pipefail` and no `|| true` around `vhs`. |
| Sandbox environment variable is ineffective. | Prefix each call as `VHS_NO_SANDBOX=true vhs "$$tape"`. |
| Embedding generation takes too long for a recording. | Load fixtures first, then run the embedding command only when it should no-op because embeddings already exist. |
| Current docs PRD lands before this work. | Reference committed GIFs from Sphinx, but keep destructive regeneration as a manual `make docs-demos-live` step. |

---

## Acceptance Criteria

- `tools/scripts/record-vhs-demos.sh` prompts with a destructive warning and requires an exact confirmation phrase.
- `docs/_tapes/` contains the four required numbered `.tape` files.
- `docs/_static/demos/` contains matching generated `.gif` files after the user runs the recording script.
- `make docs-demos-live` delegates to the script and fails on any failed recording.
- `make docs-demos-clean` removes generated GIFs only.
- Contributor docs explain prerequisites, install commands, tape conventions, and regeneration command.
- If Sphinx docs exist by implementation time, they reference the generated GIFs but do not run destructive regeneration.
- If Sphinx docs do not exist yet, README references the generated GIFs.
- `make lint` remains the repo's aggregate code gate and does not require VHS.
- The implementation agent does not run tests and does not run the tapes; handoff gives the user the command `make docs-demos-live`.

---

## Review Questions

1. Should generated GIFs be committed after you run the tapes, matching `litestar-vite`, or should recordings remain local-only artifacts?
2. Should the destructive confirmation phrase be exactly `DESTROY DEMO ENV`, or do you want a different phrase?
3. Should this PRD be implemented as a standalone docs improvement, or folded into `documentation-setup_20260429` before execution?
