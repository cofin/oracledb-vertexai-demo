# Developers

Working on the demo itself rather than just running it. The end-user
[Quickstart](quickstart.md) is the path-of-least-resistance to a running
chat. This page is the longer path: the raw migration entrypoint, the
maintainer regeneration loop, and the verification commands.

## Local environment

```bash
make install-uv      # install uv if it isn't already
make install         # Python deps + frontend deps + built Vite assets
uv run python manage.py init   # writes .env
make start-infra     # local Oracle 26ai container with vector_memory_size set
```

`manage.py init` is what writes the development `.env`; it is not part
of the end-user `coffee upgrade` flow. Run it once per checkout. If you want
commit-time hooks, run `uvx prek install`; `make lint` runs the checks on
demand either way.

## Database lifecycle (developer path)

End users should run `coffee upgrade`. Developers usually want the raw
SQLSpec migration commands so they can downgrade and re-run individual
revisions:

```bash
uv run python manage.py database upgrade --no-prompt
uv run python manage.py database downgrade --no-prompt
uv run python manage.py database current
```

The Litestar SQLSpec plugin doesn't auto-mount its `db` group onto
`coffee` — keep migration commands on `manage.py` so they don't ride app
startup hooks.

## Maintainer regeneration loop

The contributor path uses committed fixtures. Regenerating embeddings is
a maintainer operation:

```bash
make start-infra
uv run python manage.py database upgrade --no-prompt
# Refresh source rows, then:
uv run coffee bulk-embed
uv run coffee export-fixtures
```

To validate the exported fixtures from a clean database, run
`uv run coffee load-fixtures`. After that, hit `/explore` and verify the
EXPLAIN PLAN still mentions `VECTOR` rather than a full table scan.

## Verification

```bash
make lint        # prek + mypy + pyright + frontend typecheck
make test        # pytest against ephemeral Oracle (pytest-databases)
make coverage    # pytest with coverage report
```

`make test` spins up its own Oracle container via `pytest-databases` —
it doesn't share state with `make start-infra`, so the two can run side
by side.

## Where to go next

- [CLI reference](cli.md) — end-user lifecycle commands.
- [For the curious](internals.md) — HNSW, deterministic routing vs ADK
  fallback latency, and the live performance dashboard.
- [API reference](api.md) — autodoc on `ADKRunner` and core services.
