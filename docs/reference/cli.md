# CLI reference

`coffee` is the demo's lifecycle CLI — a small Click group covering the
production-app commands an end user or operator needs to upgrade, run,
enqueue/process background jobs, refresh embeddings, and inspect the app.

| Command | Purpose |
| --- | --- |
| `coffee run [--no-worker]` | Start the Litestar app via Granian (with embedded queue worker unless `--no-worker` is passed). |
| `coffee worker run` / `coffee queues run` | Start a standalone `litestar-queues` worker fleet backed by Oracle 26ai `FOR UPDATE SKIP LOCKED`. |
| `coffee worker status` / `coffee queues status` | Inspect queued, running, completed, and failed background task counts. |
| `coffee upgrade` | End-user install path: apply migrations and load committed fixtures. |
| `coffee load-fixtures` | Populate Oracle from the committed gzipped demo data (products, stores, route exemplars, embeddings). |
| `coffee bulk-embed [--enqueue]` | Generate `gemini-embedding-2` embeddings inline or enqueue `products.embed_missing` onto `litestar-queues`. |
| `coffee export-fixtures` | Dump the current database state back into committable fixture files. |
| `coffee clear-cache --force` | Prune expired responses and truncate the response and embedding caches. |
| `coffee model-info` | Print the active Vertex AI model + dimension settings. |

`bulk-embed` and `export-fixtures` live on the app CLI on purpose: they're
demo lifecycle operations, not throwaway scripts. They share the app's
runtime configuration, so the database, SQLSpec setup, `litestar-queues`
service, and Vertex AI client they touch are the same ones the running
server uses.

For the raw SQLSpec migration entrypoint and the maintainer
regeneration loop, see [Developers](developers.md).
