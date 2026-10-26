# CLI reference

Cymbal Coffee separates runtime operations into two Click command-line entrypoints:

- **`coffee`** (`src/app/cli/commands.py`) — packaged production application CLI for running the ASGI server, applying upgrades, managing fixtures and embeddings, configuring APEX CDN static assets, and operating `litestar-queues` workers.
- **`python manage.py`** (`manage.py`) — unified developer and DevOps CLI for `.env` bootstrap, container lifecycle, Oracle APEX 26.1 and APEXlang workflows, raw SQLSpec migrations, wallet diagnostics, Vite asset builds, deterministic demo video recording, and slide tooling.

## Production application CLI (`coffee`)

| Command | Purpose |
| --- | --- |
| `coffee run [--port PORT] [--host HOST] [--reload] [--workers N] [--no-worker]` | Start the Litestar ASGI server via Granian. Port precedence resolves `--port` (`-p`), `LITESTAR_PORT` (or `GRANIAN_PORT`), `PORT` (Cloud Run fallback default), and finally `8000`. Starts the embedded queue worker unless `--no-worker` is passed (`QUEUE_EXECUTION_BACKEND=none`). |
| `coffee upgrade [--revision head] [--no-fixtures] [--dry-run]` | Apply SQLSpec schema migrations up to `--revision` and load committed fixture data unless `--no-fixtures` or `--dry-run` is set. |
| `coffee load-fixtures [--tables TABLES] [--list]` | Populate Oracle tables from committed fixture files under `src/app/db/fixtures/` (`chat_route.json`, `product.json.gz`, `store.json.gz`, `store_product_inventory.json.gz`), or list available fixtures with `--list`. |
| `coffee export-fixtures [--tables TABLES] [--output-dir DIR] [--no-compress] [--list]` | Export database tables to gzipped (or uncompressed `--no-compress`) JSON fixture files, or list exportable tables with `--list`. |
| `coffee bulk-embed [--batch-size 50] [--force]` | Generate or refresh 3072-dimensional `gemini-embedding-2` embeddings for `product` and `chat_route` rows by enqueuing `products.embed_missing` through `QueueService` with `execution_backend="immediate"` (`--force` / `-f` re-embeds existing rows). |
| `coffee clear-cache [--force]` | Prune expired `response_cache` rows and clear `response_cache` and `embedding_cache` (`--force` / `-f` skips confirmation). |
| `coffee model-info` | Print active Vertex AI chat model, embedding model, Google Cloud project ID, and embedding dimensions, and verify client initialization. |
| `coffee configure-apex-cdn` | Connect as `ADMIN` (Autonomous wallet via `extract_oracle_wallet_zip`) or `SYSDBA` and run packaged PL/SQL from `src/app/db/sql/deploy/configure-apex-cdn.sql` to point `APEX_INSTANCE_ADMIN` `IMAGE_PREFIX` to Oracle's public CDN (`src/app/db/sql/deploy/revert-apex-cdn.sql` is packaged alongside it to restore `/i/`). |
| `coffee worker {run,status,run-task,run-maintenance}` | Start or inspect standalone `litestar-queues` workers backed by Oracle 26ai `FOR UPDATE SKIP LOCKED` on the isolated `queue_db_session` pool. |
| `coffee queues {run,status,run-consumer,run-maintenance,run-task,scheduler-health}` | Full `litestar-queues` operations group mounted alongside `coffee worker`. |

`bulk-embed`, `export-fixtures`, and `configure-apex-cdn` live on the packaged `coffee` CLI because they rely on `Settings.from_env()` alongside the application's Dishka container (`create_container()`), `QueueService`, or packaged SQL resources in both local checkouts and PyApp onefile builds.

## Developer and DevOps CLI (`manage.py`)

| Command | Purpose |
| --- | --- |
| `uv run python manage.py init [--mode managed\|external] [--run-install] [--run-doctor] [--non-interactive]` | Create or update `.env` for managed container mode (`adb-free:latest-26ai`) or an external Oracle 26ai database. |
| `uv run python manage.py install {all,sqlcl,mcp-toolbox,list}` | Install external tooling prerequisites including Oracle SQLcl `26.1.2+` (`~/.local/bin/sql`) and Antigravity MCP configurations. |
| `uv run python manage.py doctor [--mode managed\|external] [--json] [--verbose]` | Check `.env`, `uv`, Podman/Docker CPU and memory allocations (`>= 4` CPUs, `>= 8 GiB` RAM), container state, and `.envs/tns` ADB-Free wallet readiness. |
| `uv run python manage.py infra {start,stop,restart,status,logs,wipe}` | Manage the local `container-registry.oracle.com/database/adb-free:latest-26ai` container, which bundles Oracle APEX `26.1.5` and ORDS `26.3` natively on `https://localhost:8443/ords/apex` and exports the `.envs/tns` mTLS wallet. |
| `uv run python manage.py infra apex {status,export-openapi,generate,export,validate,import,configure-vertex}` | Report live `APEX_RELEASE` and ORDS HTTPS status, export the `/api/apex` OpenAPI 3.1 catalog, run SQLcl `26.1.2+` APEXlang source workflows, and configure `COFFEE_VERTEX_AI` (`--mode direct` or `--mode gateway`). |
| `uv run python manage.py database {upgrade,downgrade,create-migration,make-migration,show-current-revision,show-config,stamp,squash,fix,init,adk}` | Execute raw SQLSpec migration commands directly against `app.config.db` without triggering web server startup hooks. |
| `uv run python manage.py database wallet {extract,configure,list-services,validate}` | Extract `Wallet_*.zip` archives, inspect `tnsnames.ora` service aliases, and validate mTLS wallet files. |
| `uv run python manage.py database connect {test,info}` | Verify Oracle database connectivity and print resolved DSN and wallet parameters. |
| `uv run python manage.py assets {install,build,serve,generate-types}` | Install npm packages, build production Vite bundles, run the Vite dev server, or generate TypeScript types from OpenAPI routes. |
| `uv run --group demos python manage.py demos {check,shell,web,all}` | Verify VHS/Playwright/FFmpeg prerequisites and record deterministic terminal tapes (`shell` also runs without `--group demos`) and headless APEX 26.1 browser walkthroughs. |
| `uv run python manage.py slides {inventory,diff,validate,highlight,qr}` | Inspect presentation JSON dumps, validate offline `batchUpdate` payloads, highlight SQL/code cards, and render QR PNGs. |

For contributor workflows, raw migration loops, and deterministic demo video recording targets, see [Developers](developers.md).
