# Integration Test Catalog (`src/tests/integration/`)

Database-backed and HTTP integration tests (`make test-integration`) running against an ephemeral `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free` on `:1521/freepdb1`) Oracle 26ai container.

## Canonical Module Map

- `conftest.py` — session-scoped `oracle_test_container` (`ContainerFlavor.FREE`), worker-once schema migration and `.json.gz` fixture loader (`oracle_seed_data`), `driver`, `client`, and `htmx_client`.
- `db/test_sqlspec_connection.py` — SQLSpec `0.69.0` Oracle async driver connection, inline `CLOB` string materialization across `select` and `select_stream` (`fetch_lobs=False`), parameter binding, `MERGE`, generated identity `INSERT`, `VECTOR` column metadata, and Oracle 26ai `USER_ANNOTATIONS_USAGE` verification.
- `domain/chat/controllers/test_chat_http.py` — `POST /api/chat/stream` SSE event framing and `POST /api/chat/session/clear`.
- `domain/products/controllers/test_vector_http.py` — `POST /api/vector-demo` HTMX swap + `HX-Push-Url` and `GET /api/explain-plan` HTTP routes.
- `domain/products/services/test_vector_search.py` — live Oracle 26ai `vector-search-products` HNSW cosine similarity search (`FETCH APPROX`) and `ProductMatch` projection.
- `domain/web/controllers/test_pages.py` — full HTML rendering for `/` (Barista chat) and `/explore` (Vector lab).
- `server/test_static_assets.py` — `GET /favicon.ico` HTTP 200 resolution and `image/*` content-type verification.
