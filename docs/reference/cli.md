# CLI reference

`coffee` is the demo's lifecycle CLI — a small Click group covering the
production-app commands an end user needs to upgrade, run, refresh, and
inspect the app.

| Command | Purpose |
| --- | --- |
| `coffee run` | Start the Litestar app via Granian. |
| `coffee upgrade` | End-user install path: apply migrations and load committed fixtures. |
| `coffee load-fixtures` | Populate Oracle from the committed gzipped demo data (products, stores, embeddings). |
| `coffee bulk-embed` | Generate `gemini-embedding-2-preview` embeddings for any catalog rows still missing them. |
| `coffee export-fixtures` | Dump the current database state back into committable fixture files. |
| `coffee clear-cache --force` | Truncate the response cache and the embedding cache. |
| `coffee model-info` | Print the active Vertex AI model + dimension settings. |

`bulk-embed` and `export-fixtures` live on the app CLI on purpose: they're
demo lifecycle operations, not throwaway scripts. They share the app's
runtime configuration, so the database, SQLSpec setup, and Vertex AI
client they touch are the same ones the running server uses.

For the raw SQLSpec migration entrypoint and the maintainer
regeneration loop, see [Developers](developers.md).
