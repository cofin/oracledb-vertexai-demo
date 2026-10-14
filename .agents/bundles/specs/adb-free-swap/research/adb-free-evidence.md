---
type: Research
research_id: adb-free-evidence
title: ADB-Free 26ai container evidence for adb-free-swap
scope: integration
tags: [migration, oracle-26ai, infrastructure]
status: stable
state: promoted
promoted_to: adb-free-swap
created_at: 2026-10-13T19:15:00Z
updated_at: 2026-10-13T19:15:00Z
---

# ADB-Free 26ai Container Evidence

Collected 2026-10-13 during planning. Confidence: high = primary source or this repository's history; medium = consistent secondary sources or indirect repository evidence.

## Findings

| ID | Finding | Confidence | Citations |
| --- | --- | --- | --- |
| F1 | The image is now named "Oracle Autonomous AI Database Free Container Image". 26ai tags: `latest-26ai` = `26.9.4.1-26ai`, multi-arch (`linux/amd64`, `linux/arm64`); 19c `latest` = `26.9.4.2`. The README pulls `ghcr.io/oracle/adb-free:latest-26ai`; the June 2026 code pulled `container-registry.oracle.com/database/adb-free:latest-26ai`. | high | `https://raw.githubusercontent.com/oracle/adb-free/main/README.md` (fetched 2026-10-13); `git show a7b9112:tools/oracle/database.py` |
| F2 | The container needs 4 CPUs and 8 GiB memory; storage is capped at 20 GB per database. | high | README "Container CPU/memory requirements" |
| F3 | Run contract: `-p 1521:1522 -p 1522:1522 -p 8443:8443 -p 27017:27017 -e WORKLOAD_TYPE=ATP -e WALLET_PASSWORD=... -e ADMIN_PASSWORD=... --cap-add SYS_ADMIN --device /dev/fuse`. Optional `DATABASE_NAME` (default `MYATP`) and `ENABLE_ARCHIVE_LOG` (default true). Port table: 1521 TLS, 1522 mTLS, 8443 HTTPS for ORDS/APEX/Database Actions, 27017 Mongo API. ADMIN password: 12-30 characters with upper, lower, and digit, not containing the username; wallet password: at least 8 characters mixing letters with numbers or specials. | high | README "Starting an ADB Free container", "Ports", environment variable table |
| F4 | Data persists across container restarts and removals when a volume is mounted at `/u01/data`. | high | README "Mount Volume" |
| F5 | The wallet is generated at `/u01/app/oracle/wallets/tls_wallet`; copy it with `podman cp` and point `TNS_ADMIN` at it. mTLS aliases: `myatp_medium`, `myatp_high`, `myatp_low`, `myatp_tp`, `myatp_tpurgent`; TLS aliases add `_tls`. Walletless TLS requires trusting `/u01/app/oracle/wallets/tls_wallet/adb_container.cert`. python-oracledb example: `oracledb.connect(user=..., password=..., dsn="myadw_medium", config_dir=..., wallet_location=..., wallet_password=...)`. | high | README "Wallet Setup", "Available TNS aliases", "TLS walletless connection", "Python" |
| F6 | App user recipe as ADMIN: `CREATE USER ... QUOTA UNLIMITED ON DATA`; `GRANT CONNECT, CONSOLE_DEVELOPER, DWROLE, RESOURCE`; `ORDS.ENABLE_SCHEMA(...)`. | high | README "Create an app user"; `git show a7b9112:tools/oracle/database.py` (`_build_app_user_statements`) |
| F7 | `adb-cli` documents `add-database` and `change-password`; the June live container also listed `change-expired-password`, `cleanup-container-data-dir`, `export`, `import`, `set-http-proxy`. No APEX or upgrade command. | high | README "adb-cli"; `git show a7b9112:.agents/research/research_apex_upgrade/research.md` |
| F8 | ADB-Free denies `sqlplus / as sysdba` (ORA-01017); ADMIN is the ceiling. The June image (`26.2.4.2-26ai`) shipped APEX 24.2.14, ORDS 26.1.0, and DB 23.26.2.1.0. | high for that image | `git show a7b9112:.agents/research/research_apex_upgrade/research.md` (live-validated 2026-06-14); `git show 900d04d:.agents/specs/apex-gvenzl-install/prd.md` |
| F9 | ADB-Free has no init or startup hook directories; post-start work runs through SQL clients. | high | `git show a7b9112:.agents/research/research_adb_hooks_ux_lab/research.md`; README |
| F10 | Autonomous AI Database manages the vector pool elastically: it grows when HNSW indexes are created or a PDB with HNSW indexes reopens, PDB-level `VECTOR_MEMORY_SIZE` stays 0 and cannot be set with `ALTER SYSTEM`, and growth is not persisted to the SPFILE. Monitor with `V$VECTOR_MEMORY_POOL` (`POOL`, `ALLOC_BYTES`, `USED_BYTES`, `POPULATE_STATUS`, `CON_ID`). | medium: Oracle ADB-S and AI Vector Search docs via search summaries; container parity unverified | Web searches 2026-10-13 ("elastic vector memory", `V$VECTOR_MEMORY_POOL`); repository history: June ADB-Free ran the HNSW migrations while the SYSDBA vector step could not succeed |
| F11 | Autonomous AI Database enables the In-Memory column store through the console or API as a percentage of SGA (ECPU model), not through SQL. The free container has no console. Expect `inmemory_size = 0`. `V$IM_SEGMENTS` lists only populated segments (`OWNER`, `SEGMENT_NAME`, `POPULATE_STATUS`, `BYTES_NOT_POPULATED`, `INMEMORY_SIZE`). | medium | Web searches 2026-10-13 (ADB Database In-Memory enablement; Oracle Reference `V$IM_SEGMENTS`) |
| F12 | Select AI Google provider: credential `username => 'GOOGLE'`, `password => <Google AI Studio key>`; profile `"provider": "google"`; ACL `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(host => 'generativelanguage.googleapis.com', ace => xs$ace_type(privilege_list => xs$name_list('http'), ...))`; ADMIN must `GRANT EXECUTE ON DBMS_CLOUD_AI`, while `DWROLE` covers `DBMS_CLOUD`. No Vertex AI provider. | high | `.agents/bundles/knowledge/presentation/verified-facts.md` (Oracle docs cited there); Select AI prerequisite search 2026-10-13 |
| F13 | Behind a proxy, `DBMS_CLOUD_CONTAINER_ADMIN.set_database_property('HTTP_PROXY', 'host:port/')` configures `DBMS_CLOUD` egress. | high | README "HTTP proxy" |
| F14 | `DB_DEVELOPER_ROLE` nests `CTXAPP`, which covers the `CTX_DDL` preference calls in migration 0001. | medium | oracle-base `DB_DEVELOPER_ROLE` article via search 2026-10-13 |
| F15 | `INMEMORY` table clauses executed on ADB-Free in June (SQLSpec extension tables with `in_memory=True`) without migration failures. | medium (indirect) | `git show a7b9112:src/app/lib/settings.py` (`ORACLE_ADK_IN_MEMORY` default true) with live ADB-Free use on 2026-06-14 |
| F16 | `DBMS_CLOUD_AI` is absent from gvenzl Oracle AI Database 26ai Free (`23.26.0.0.0`). | high | `.agents/bundles/knowledge/presentation/verified-facts.md` |

## Contradictions

- C1 (unresolved by docs): the README maps host 1521 to container 1522, while its port table lists 1521 as TLS. The plan follows the README run command, which the June implementation also used successfully over the mTLS wallet. Task 2.1 asserts the observed walletless TLS behavior and defines both outcomes.
- C2 (resolved for June): `research_apex_integration` (2026-06-13) claimed `latest-26ai` shipped APEX 26.1; the 2026-06-14 live check showed 24.2.14. The current `26.9.4.1-26ai` APEX version is unverified; Task 1.1 records it.

## Limitations

- `docs.oracle.com` and `cdn.jsdelivr.net` fetches were denied in this session. Oracle documentation facts come from search summaries and the repository's verified-facts chapter.
- No ADB-Free container was run during planning. Tasks 1.1, 1.2, 2.1, 2.2, and 2.3 capture live evidence in their Notes.
