# Developers

Working on the demo itself rather than just running it. The end-user
[Quickstart](quickstart.md) is the path-of-least-resistance to a running
chat. This page covers local setup, raw SQLSpec migration commands, APEXlang
and Vertex AI developer loops, deterministic demo video recording, and
repository verification gates.

## Local environment

```bash
make install-uv                  # install uv if it is not already on PATH
make install                     # Python 3.12 venv + dev groups + npm + Vite bundle
uv run python manage.py init     # write .env (managed or external mode)
uv run python manage.py doctor   # verify Docker/Podman resources and .envs/tns wallet readiness
make start-infra                 # start adb-free:latest-26ai (APEX 26.1.5 + ORDS 26.3 on :8443)
make apex                        # check live APEX_RELEASE and ORDS HTTPS readiness
make install-sqlcl               # install SQLcl 26.1.2+ to ~/.local/bin for APEXlang workflows
```

`manage.py init` writes the development `.env`; it is not part of the end-user
`coffee upgrade` flow. Run it once per checkout. `make start-infra` launches
`container-registry.oracle.com/database/adb-free:latest-26ai`, which bundles
Oracle APEX `26.1.5` and ORDS `26.3` natively on `https://localhost:8443/ords/apex`
and exports the `.envs/tns` mTLS wallet automatically. If you want commit-time
hooks, run `uvx prek install`; `make lint` runs the full static gate on demand.

## Database lifecycle (developer path)

End users initialize schemas and fixtures with `coffee upgrade`. Contributors
working on migrations or wallet connectivity use `manage.py database`:

```bash
uv run python manage.py database upgrade --no-prompt
uv run python manage.py database downgrade --no-prompt
uv run python manage.py database show-current-revision
uv run python manage.py database wallet validate
uv run python manage.py database connect test
```

The custom `_SQLSpecPlugin` wrapper in `src/app/server/plugins.py` suppresses
auto-mounting SQLSpec's `db` group onto `coffee` so migration commands stay on
`manage.py` without invoking web server startup hooks.

## Oracle APEX 26.1 and APEXlang loop

With `adb-free:latest-26ai` running and SQLcl `26.1.2+` installed, manage the
`COFFEE_VERTEX_AI` Generative AI Service and the source-controlled
`src/apex/cymbal-coffee-ops/` application through `manage.py infra apex`:

```bash
uv run python manage.py infra apex configure-vertex --mode direct --verify
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops
uv run python manage.py infra apex export-openapi
```

On workstations where outbound database egress is restricted or mTLS
Context-Aware Access is required, pass `--mode gateway` to route APEX
requests through `ApexAIController` (`http://host.docker.internal:8000/api/apex/ai/v1`).

## Maintainer regeneration loop

The contributor path uses committed fixtures under `src/app/db/fixtures/`.
Regenerating `gemini-embedding-2` vectors is a maintainer operation driven by
`QueueService` (`products.embed_missing` with `execution_backend="immediate"`):

```bash
make start-infra
uv run python manage.py database upgrade --no-prompt
uv run coffee bulk-embed
uv run coffee export-fixtures
```

To validate exported fixtures from a clean database, run
`uv run coffee load-fixtures`. Afterward, open `/explore` and verify the live
`EXPLAIN PLAN` uses the `VECTOR` and `DOMAIN INDEX` paths rather than a full
table scan.

## Deterministic demo video recordings

Terminal and APEX 26.1 browser walkthrough videos (`.mp4` and palette-optimized
`.gif` under `docs/_static/demos/`) are scripted and reproducible via
`tools/demos/{cli,shell,web}.py`, VHS tapes in
`docs/_tapes/{apex-vertex-ai-setup,apexlang-workflow}.tape`, and the optional
`demos` dependency group (`[dependency-groups].demos = ["playwright>=1.50"]`):

```bash
# Install Playwright and headless Chromium for browser and VHS Rod capture
uv sync --group demos
uv run --group demos playwright install chromium

# Verify vhs, ttyd, ffmpeg, headless Chromium, and playwright.sync_api
uv run --group demos python manage.py demos check

# Record VHS terminal & SQLcl tapes (docs/_tapes/*.tape)
make docs-demos-shell

# Record headless Playwright + FFmpeg APEX 26.1 browser scenarios
make docs-demos-web

# Interactive live recording of both shell and browser demos (tools/scripts/record-live-demos.sh)
make docs-demos-live

# Clean generated .mp4, .gif, and .webm media under docs/_static/demos/
make docs-demos-clean
```

`tools/demos/web.py` records the `apex-configure-vertex-ai` and
`apex-create-vertex-app` scenarios at `1280x720` (`15 fps`) with an injected
cursor/caption HUD, then transcodes the raw WebM capture to H.264 `yuv420p`
`+faststart` `.mp4` and Lanczos palette `.gif` via FFmpeg.

## Verification and CI gates

```bash
make lint              # prek + Ruff + hygiene/security/review gates + mypy + pyright + slotscheck + dependency-smoke + tsc
make test-unit         # fast isolated unit tests and AST meta-guards (no Oracle container required)
make test-integration  # live Oracle 26ai integration suite against ephemeral gvenzl/oracle-free
make test              # full unit + integration test suite
make coverage          # pytest with HTML and XML coverage reports
make docs              # Sphinx HTML build with warnings treated as errors (-W --keep-going)
```

`tools/ci/check_code_hygiene.py` inspects `src/app/`, `tools/`, and `manage.py`
to enforce module docstrings, top-level imports, `@dataclass(slots=True)`,
public-before-private symbol ordering, Dishka provider annotation rules in
`src/app/ioc/`, and zero non-directive inline `#` comments. `make test-integration`
manages its own ephemeral `gvenzl/oracle-free` container in
`src/tests/integration/conftest.py`, so it does not mutate the persistent
`adb-free:latest-26ai` container started by `make start-infra`.

## Where to go next

- [CLI reference](cli.md) — `coffee` production commands and `manage.py` DevOps commands.
- [For the curious](internals.md) — SQLSpec `0.69.0`, HNSW, single-query Hybrid RRF routing, and the live performance dashboard.
- [API reference](api.md) — HTTP/MCP/A2A route catalog and autodoc on controllers, `AgentOrchestrationService`, `HybridRouteResolver`, services, and schemas.
