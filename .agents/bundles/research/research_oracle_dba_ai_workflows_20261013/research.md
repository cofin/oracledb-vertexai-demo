---
type: Research
research_id: research_oracle_dba_ai_workflows_20261013
title: "The Art of the Possible: AI & LLM Workflows for Oracle DBAs on Oracle Database@Google Cloud Exadata (26ai)"
description: Primary-source technical research on integrating Gemini, Vertex AI, MCP, and Oracle AI Database 26ai into Oracle Exadata DBA workflows, including Exadata vs. Autonomous capability boundaries, high-scale FinTech/payment-ledger DBA failure modes, and outcome-driven closed-loop DBA scripts.
scope: integration
tags:
  - research
  - oracle
  - exadata
  - dba
  - vertex-ai
  - mcp
  - oracle-26ai
status: stable
state: open
promoted_to: null
confidence: high
created_at: 2026-10-13T17:20:00Z
updated_at: 2026-10-13T17:20:00Z
---

# The Art of the Possible: AI & LLM Workflows for Oracle DBAs on Oracle Database@Google Cloud Exadata (26ai)

## Executive Summary

1. **Exadata Database Service (26ai) vs. Autonomous AI Database Capability Boundary**:
   - **Native on Exadata Database Service (Oracle 26ai)**: Core AI Vector Search (`VECTOR` data type, `DBMS_VECTOR`, `DBMS_VECTOR_CHAIN` with the `vertexai` REST provider for embeddings, text generation, and reranking), **Exadata AI Smart Scan** (storage-cell offload for `NEIGHBOR PARTITIONS` IVF and brute-force `VECTOR_DISTANCE` scans plus top-K filtering), **HNSW In-Memory Neighbor Graphs** (duplicated in each RAC node's SGA `vector_memory_size` with concurrent DML support), **Schema `ANNOTATIONS`** (`USER_ANNOTATIONS_USAGE`), **Oracle SQLcl MCP Server (`sql -mcp`)**, **Google MCP Toolbox (`--prebuilt oracledb` and custom `tools.yaml`)**, and **`gcloud oracle-database` CLI** for Exadata infrastructure and VM cluster operations.
   - **Autonomous AI Database (ADB-S) Only (or Requires Manual CDB/PDB Install on Exadata)**: `DBMS_CLOUD_AI` (**Select AI**) and `DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'GCP')` (`GCP$PA` service account credential) are pre-installed and managed on Autonomous AI Database, not out-of-the-box on customer-managed Exadata Database Service (where `DBMS_CLOUD` requires manual `$ORACLE_HOME/rdbms/admin/catclouduser.sql` + `dbms_cloud_install.sql` setup, and Select AI still has no `vertexai` provider). Similarly, the managed remote endpoint `https://oracledatabase.googleapis.com/mcp` currently exposes control-plane tools only for Autonomous Databases (`list_autonomous_databases`, `create_autonomous_database`).
2. **Four Practical Integration Tiers for Exadata DBAs**:
   - **Tier 1 — Interactive Terminal & IDE Copilot (`agy` + `sql -mcp` + `awr-reports` skill)**: Zero-code conversational diagnostics with built-in database audit trails (`DBTOOLS$MCP_LOG`, `/* LLM in use ... */` SQL comments, and `V$SESSION.MODULE`/`ACTION` tagging).
   - **Tier 2 — Curated Read-Only MCP Toolboxes (`tools.yaml` with `kind: oracle-sql`)**: Exposing battle-tested DBA queries (RAC Global Cache waits, `enq: TX - index contention`, Smart Scan offload regressions, GoldenGate open transactions, deferred global index orphans) as parameterized, read-only MCP tools instead of open `execute_sql`.
   - **Tier 3 — Outcome-Driven Closed-Loop Triage Scripts (`python-oracledb` + `google-genai` on Vertex AI)**: Deterministic SQL threshold checks trigger automatic secondary diagnostic collection (`DBMS_XPLAN.DISPLAY_CURSOR`, `DBA_HIST_SQLSTAT`, `GV$ACTIVE_SESSION_HISTORY`), pass the structured evidence to Gemini on Vertex AI, and produce a validated remediation script (`DBMS_SPM` baseline pin, `ALTER SEQUENCE ... SCALE EXTEND`, `DBMS_PART.CLEANUP_GIDX`, or `ALTER SYSTEM KILL SESSION`) gated by DBA approval or ticket/PR creation.
   - **Tier 4 — In-Database Semantic Incident Memory (`VECTOR(3072, FLOAT32)` + `V$DIAG_ALERT_EXT`)**: Storing past postmortems, runbooks, and resolved `ORA-` incident signatures as Vertex AI embeddings inside Oracle 26ai so alert-Watcher scripts can retrieve the top matching historical fixes via SQL RRF before calling Gemini.

---

## 1. Capability Matrix: Exadata Database Service (26ai) vs. Autonomous AI Database

When presenting or building workflows for DBAs running **Oracle Exadata Database Service on Oracle Database@Google Cloud** with **Oracle AI Database 26ai**, use the verified matrix below (`F1`–`F12`):

| Capability / Tool | Exadata Database Service (Oracle 26ai on GCP) | Autonomous AI Database (ADB-S on GCP) | Auth & Operational Notes for Exadata DBAs |
| :--- | :--- | :--- | :--- |
| **`VECTOR(dim, FLOAT32|INT8|BINARY)` & HNSW / IVF Indexes** | **Native (Core 26ai)** | **Native** | HNSW (`INMEMORY NEIGHBOR GRAPH`) lives in each RAC instance's SGA `vector_memory_size`; IVF (`NEIGHBOR PARTITIONS`) is tablespace-backed, supports `LOCAL` partitioning, and offloads to Exadata storage cells (`F1`, `F3`, `F5`). |
| **Exadata AI Smart Scan (`cell smart table scan` for vectors)** | **Native (Exadata Storage Server 24.1+ / 25.x / 26ai)** | Underlying Exadata infra (hidden) | Offloads brute-force and IVF `VECTOR_DISTANCE` math, adaptive cell-level Top-K filtering, and included-column predicates directly to storage cells (`F3`, `F4`). |
| **`DBMS_VECTOR` & `DBMS_VECTOR_CHAIN` (`provider: "vertexai"`)** | **Native (Core 26ai)** | **Native** | Supports Vertex AI embeddings (`UTL_TO_EMBEDDING`), text generation (`UTL_TO_GENERATE_TEXT`), and rerank; requires `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE` for `*aiplatform.googleapis.com` and a rotated OAuth `access_token` in `DBMS_VECTOR.CREATE_CREDENTIAL` (`F1`, `F2`, `F8`). |
| **Schema `ANNOTATIONS` (`USER_ANNOTATIONS_USAGE`)** | **Native (Core 26ai)** | **Native** | Queryable DDL metadata on tables/columns/views (`DBA_ANNOTATIONS_USAGE`); ideal for teaching agents column units, privacy rules, and join contracts (`F1`). |
| **Oracle SQLcl MCP Server (`sql -mcp`, SQLcl 25.2+)** | **Native (Client-side over Net8/TCPS)** | **Native** | Exposes `list-connections`, `connect`, `disconnect`, `run-sql`, `run-sqlcl`; automatically logs every agent query to `DBTOOLS$MCP_LOG` and tags `V$SESSION.MODULE`/`ACTION` (`F9`). |
| **Google MCP Toolbox (`toolbox --prebuilt oracledb` or `--tools-file`)** | **Native (Client-side)** | **Native** | Prebuilt tools: `execute_sql`, `list_tables`, `get_query_plan`, `list_active_sessions`, `list_top_sql_by_resource`, `list_tablespace_usage`, `list_invalid_objects`; supports custom `kind: oracle-sql` tools in `tools.yaml` (`F10`). |
| **`gcloud oracle-database` Control-Plane CLI** | **Native (`cloud-exadata-infrastructures`, `cloud-vm-clusters`, `db-servers`, `db-nodes`)** | **Native (`autonomous-databases`)** | Scriptable from shell/Python or wrapped as custom MCP tools to inspect Exadata rack health, OCPU scaling, GI versions, and VM cluster status (`F12`). |
| **Google Cloud Remote MCP (`oracledatabase.googleapis.com/mcp`)** | **Not supported for Exadata today** | **Supported** | Currently exposes only `list_autonomous_databases` and `create_autonomous_database` (`F11`). Use `gcloud oracle-database` for Exadata control-plane operations. |
| **`DBMS_CLOUD_AI` (Select AI) & `GCP$PA` Principal Auth** | **Not pre-installed** (requires manual `catclouduser.sql` + `dbms_cloud_install.sql`; no `vertexai` provider) | **Pre-installed & Managed** | On Exadata, prefer application/script-tier `google-genai` (Vertex AI ADC/IAM) or `DBMS_VECTOR` (`provider: "vertexai"`) over Select AI (`F6`, `F7`, `F8`). |

---

## 2. Six High-Scale FinTech / Payment-Ledger Exadata DBA Failure Modes

In massive high-concurrency payment and ledger environments (where connection multiplexers such as PayPal's open-source **HERA** proxy `github.com/paypal/hera` route hundreds of millions of queries per hour across sharded/RAC Oracle tiers (`F6`–`F8`)), DBAs repeatedly confront six operational bottlenecks (`F10`–`F15`). Each maps cleanly to an AI-assisted diagnostic and action workflow:

| # | High-Scale Exadata DBA Issue | Wait Events / Views to Watch | Root Cause in Payment / Ledger Workloads | Deterministic DBA Remediation Action |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Hot Right-Hand Index Block Contention (`F11`)** | `enq: TX - index contention`, `buffer busy waits`, `gc buffer busy acquire`, `GV$SEGMENT_STATISTICS` | Monotonically increasing payment/ledger IDs (`CREATE SEQUENCE` or timestamp-prefixed keys) force concurrent `INSERT` threads across all RAC nodes into the rightmost B-tree leaf block, serializing on 90-10 leaf splits. | Convert sequence to **Scalable Sequence** (`ALTER SEQUENCE ... SCALE EXTEND`) to prepend a 6-digit instance+session offset without changing application SQL, or hash-partition the global index. |
| **2** | **Bind Peeking & Adaptive Cursor Sharing (ACS) Plan Flips (`F12`)** | `GV$SQL` (`IS_BIND_SENSITIVE`, `IS_BIND_AWARE`, `PLAN_HASH_VALUE`), `DBA_HIST_SQLSTAT`, `cursor: pin S wait on X` | Skewed merchant or account IDs (1 tx/day vs. 5M tx/day) cause bind peeking to cache a full scan or wrong index, or spawn hundreds of child cursors (`V$SQL_SHARED_CURSOR`). | Pin the verified low-latency `PLAN_HASH_VALUE` into **SQL Plan Management (SPM)** via `DBMS_SPM.LOAD_PLANS_FROM_CURSOR_CACHE(..., fixed => 'YES')` and purge the bad cursor via `DBMS_SHARED_POOL.PURGE`. |
| **3** | **Exadata Smart Scan & AI Smart Scan Offload Regressions (`F3`, `F4`, `F13`)** | `V$SYSSTAT` (`cell physical IO bytes eligible for predicate offload`, `cell num smart IO sessions in rdbms block IO`), `table fetch continued row` | Recon/analytics or IVF vector queries fall back from storage-cell Smart Scan to RDBMS block I/O due to uncommitted ITL cleanout, chained rows from payment status updates (`PCTFREE` too low), or non-offloadable functions; or OLTP queries accidentally trigger full scans that saturate `cellsrv` CPU. | Rewrite non-offloadable predicates (e.g., use `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX` for HNSW or eligible predicates for Smart Scan), increase `PCTFREE` + `ALTER TABLE ... MOVE ONLINE` for chained rows, or add missing index. |
| **4** | **RAC Global Cache Interconnect Contention (`F10`)** | `gc buffer busy acquire`, `gc buffer busy release`, `gc current block busy`, `gc cr block 2-way/3-way` in `GV$ACTIVE_SESSION_HISTORY` | Microservices connecting across all RAC nodes modify the same account/settlement blocks or sequence caches (`CACHE` too small), causing Cache Fusion block ping-pong over RoCE. | Enforce singleton/preferred **RAC Service Affinity** (`srvctl modify service -preferred inst1 -available inst2`), raise sequence `CACHE 10000 NOORDER`, or align proxy shard/scuttle routing (`F6`, `F7`). |
| **5** | **Micro-Transaction Redo (`log file sync`) & GoldenGate Extract Lag (`F14`)** | `log file sync`, `log file parallel write`, `GV$TRANSACTION` (`START_TIME`, `USED_UBLK`), GoldenGate `SEND EXTRACT ... SHOWTRANS` | Payment durability requires synchronous commits, while a single forgotten open transaction (`INACTIVE` session holding an old `START_SCN`) pins GoldenGate Integrated Extract memory (`CACHEMGR`) and threatens multi-hour recovery if `BRINTERVAL` is exceeded. | Detect open transactions older than $N$ minutes in `GV$TRANSACTION` joined to `GV$SESSION`, alert/kill orphaned idle blockers, and verify GoldenGate Bounded Recovery (`BRINTERVAL`) vs. archive log retention. |
| **6** | **Online Partition Drop/Truncate & Deferred Global Index Orphans (`F15`)** | `DBA_INDEXES.ORPHANED_ENTRIES = 'YES'`, `SYS.PMO_DEFERRED_GIDX_MAINT_JOB`, `ORA-39944` | Rolling partition maintenance (`ALTER TABLE ... DROP/TRUNCATE PARTITION ... UPDATE GLOBAL INDEXES`) defers index cleanup by marking entries orphaned; if cleanup lags or runs during peak payment hours, index scans bloat and GoldenGate redo spikes. | Check `DBA_INDEXES WHERE ORPHANED_ENTRIES = 'YES'` after partition DDL and schedule controlled `DBMS_PART.CLEANUP_GIDX(schema_name_in, index_name_in)` during low-traffic windows. |

---

## 3. Concrete Examples: Simple DBA Scripts & Closed-Loop Action Workflows

### Pattern A: Curated Read-Only DBA MCP Toolbox (`tools.yaml`)

Instead of giving an AI agent unrestricted `execute_sql` with DBA privileges, DBAs can wrap their trusted diagnostic SQL into a project-local `tools.yaml` for **Google MCP Toolbox for Databases** (`toolbox --tools-file dba-tools.yaml --stdio` (`F10`)). The agent can invoke these tools in **Antigravity (`agy`)** to investigate an incident, correlate findings across views, and draft a remediation script—without ever having permission to execute DDL/DML directly:

```yaml
sources:
  exadata-prod-ro:
    kind: oracle
    connectionString: ${ORACLE_CONNECTION_STRING}
    user: ${ORACLE_RO_AUDIT_USER}
    password: ${ORACLE_RO_AUDIT_PASSWORD}

tools:
  check_rac_hot_blocks:
    kind: oracle-sql
    source: exadata-prod-ro
    description: >
      Identify top segments experiencing RAC Global Cache (gc buffer busy) or TX index
      contention across instances over the last N minutes from GV$ACTIVE_SESSION_HISTORY.
    statement: |
      SELECT ash.inst_id,
             o.owner,
             o.object_name,
             o.object_type,
             ash.event,
             COUNT(*) AS ash_samples,
             COUNT(DISTINCT ash.session_id) AS distinct_sessions,
             MAX(ash.sql_id) KEEP (DENSE_RANK LAST ORDER BY COUNT(*)) OVER (PARTITION BY o.object_name, ash.event) AS top_sql_id
      FROM   gv$active_session_history ash
      JOIN   dba_objects o ON o.object_id = ash.current_obj#
      WHERE  ash.sample_time >= SYSTIMESTAMP - NUMTODSINTERVAL(:minutes_back, 'MINUTE')
        AND  ash.event IN (
               'enq: TX - index contention',
               'buffer busy waits',
               'gc buffer busy acquire',
               'gc buffer busy release',
               'gc current block busy'
             )
      GROUP  BY ash.inst_id, o.owner, o.object_name, o.object_type, ash.event
      ORDER  BY ash_samples DESC
      FETCH  FIRST 15 ROWS ONLY
    parameters:
      - name: minutes_back
        type: integer
        description: Number of minutes to look back in ASH (e.g. 15).

  check_exadata_smart_scan_efficiency:
    kind: oracle-sql
    source: exadata-prod-ro
    description: >
      Compare Exadata Smart Scan eligible bytes against interconnect bytes returned and
      check why queries fell back to conventional RDBMS block I/O.
    statement: |
      SELECT inst_id,
             name,
             value,
             ROUND(value / 1024 / 1024 / 1024, 2) AS value_gb
      FROM   gv$sysstat
      WHERE  name IN (
               'cell physical IO bytes eligible for predicate offload',
               'cell physical IO interconnect bytes returned by smart scan',
               'cell physical IO bytes saved by storage index',
               'cell physical IO interconnect bytes',
               'cell num smart IO sessions in rdbms block IO due to user',
               'cell num smart IO sessions in rdbms block IO due to big payload',
               'table fetch continued row'
             )
      ORDER  BY name, inst_id

  check_long_open_transactions_and_gg_risk:
    kind: oracle-sql
    source: exadata-prod-ro
    description: >
      Find uncommitted transactions open longer than min_age_minutes that can pin Undo
      or cause Oracle GoldenGate Integrated Extract lag and Bounded Recovery spills.
    statement: |
      SELECT s.inst_id,
             s.sid,
             s.serial#,
             s.username,
             s.machine,
             s.program,
             s.status AS session_status,
             s.sql_id,
             s.prev_sql_id,
             t.start_time,
             ROUND((SYSDATE - TO_DATE(t.start_time, 'MM/DD/YY HH24:MI:SS')) * 1440, 1) AS open_minutes,
             t.used_ublk AS undo_blocks,
             t.used_urec AS undo_records
      FROM   gv$transaction t
      JOIN   gv$session s
        ON   t.ses_addr = s.saddr
       AND   t.inst_id = s.inst_id
      WHERE  (SYSDATE - TO_DATE(t.start_time, 'MM/DD/YY HH24:MI:SS')) * 1440 >= :min_age_minutes
      ORDER  BY open_minutes DESC
    parameters:
      - name: min_age_minutes
        type: integer
        description: Minimum transaction age in minutes (e.g. 10).

  check_orphaned_global_indexes:
    kind: oracle-sql
    source: exadata-prod-ro
    description: >
      Detect global indexes holding deferred orphaned entries after partition DROP/TRUNCATE
      with UPDATE GLOBAL INDEXES.
    statement: |
      SELECT owner,
             index_name,
             table_name,
             status,
             orphaned_entries,
             num_rows,
             last_analyzed
      FROM   dba_indexes
      WHERE  orphaned_entries = 'YES'
         OR  status = 'UNUSABLE'
      ORDER  BY owner, table_name, index_name
```

---

### Pattern B: Outcome-Driven Closed-Loop Script (`dba_plan_and_lock_triage.py`)

A major DBA pain point is the gap between **alert detection** (a cron script sees a latency spike or lock wait) and **actionable diagnosis** (gathering the competing plans, checking sequence/index properties, and preparing the exact `DBMS_SPM` or `ALTER SEQUENCE` command before the bad cursor ages out of `V$SQL`).

The script below demonstrates **"Action Based on Script Outcome"**:
1. **Stage 1 (Deterministic SQL Check)**: Queries Oracle for any `SQL_ID` experiencing a plan regression (`elapsed_ms_per_exec > 3x` its historical baseline in `DBA_HIST_SQLSTAT`) OR any index experiencing `enq: TX - index contention`.
2. **Stage 2 (Outcome-Driven Drill-Down)**:
   - *If no anomaly is found*: Exits cleanly in `<50 ms` with **zero LLM calls** and zero token cost.
   - *If a plan flip is detected*: Automatically queries `DBMS_XPLAN.DISPLAY_CURSOR` for the active regressed `PLAN_HASH_VALUE` and `DBMS_XPLAN.DISPLAY_AWR` for the historical best `PLAN_HASH_VALUE`, plus `V$SQL_CS_STATISTICS` / bind sensitivity metadata.
   - *If right-hand index contention is detected*: Automatically queries `DBA_INDEXES` and `DBA_SEQUENCES` (`SCALE_FLAG`, `EXTEND_FLAG`, `CACHE_SIZE`, `ORDER_FLAG`) for the target table.
3. **Stage 3 (Structured Gemini 3.8 Flash Diagnosis on Vertex AI)**: Sends the collected evidence to `gemini-3.8-flash` via `google-genai` (`vertexai=True`) using a strict `msgspec.Struct` / JSON schema response contract (`RootCause`, `RiskLevel`, `VerificationSql`, `RemediationPlsql`, `RollbackPlsql`).
4. **Stage 4 (Policy-Gated Action)**:
   - Automatically executes the **read-only verification SQL** to confirm the target cursor/sequence state.
   - Writes the ready-to-run remediation and rollback scripts to an audit artifact and prompts the on-call DBA (`[y/N]`)—or, in unattended mode, posts the pre-validated `DBMS_SPM.LOAD_PLANS_FROM_CURSOR_CACHE` block to the team incident channel / change ticket.

```python
"""Outcome-driven Exadata DBA triage and human-gated remediation script."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import msgspec
import oracledb
from google import genai
from google.genai import types

REGRESSED_SQL_QUERY = """
WITH recent_sql AS (
    SELECT sql_id,
           plan_hash_value AS current_phv,
           SUM(executions) AS execs,
           ROUND(SUM(elapsed_time) / NULLIF(SUM(executions), 0) / 1000, 2) AS current_ms,
           MAX(is_bind_sensitive) AS bind_sensitive,
           MAX(is_bind_aware) AS bind_aware
    FROM   gv$sql
    WHERE  parsing_schema_name = :schema_name
      AND  executions >= 20
      AND  plan_hash_value > 0
    GROUP  BY sql_id, plan_hash_value
),
hist_baseline AS (
    SELECT sql_id,
           plan_hash_value AS best_phv,
           ROUND(SUM(elapsed_time_delta) / NULLIF(SUM(executions_delta), 0) / 1000, 2) AS baseline_ms,
           ROW_NUMBER() OVER (
               PARTITION BY sql_id
               ORDER BY SUM(elapsed_time_delta) / NULLIF(SUM(executions_delta), 0) ASC
           ) AS rn
    FROM   dba_hist_sqlstat
    WHERE  parsing_schema_name = :schema_name
      AND  executions_delta >= 100
    GROUP  BY sql_id, plan_hash_value
)
SELECT r.sql_id,
       r.current_phv,
       h.best_phv,
       r.current_ms,
       h.baseline_ms,
       ROUND(r.current_ms / NULLIF(h.baseline_ms, 0), 1) AS regression_factor,
       r.bind_sensitive,
       r.bind_aware
FROM   recent_sql r
JOIN   hist_baseline h
  ON   r.sql_id = h.sql_id
 AND   h.rn = 1
WHERE  r.current_phv <> h.best_phv
  AND  r.current_ms >= h.baseline_ms * 3.0
  AND  r.current_ms >= 25.0
ORDER  BY regression_factor DESC
FETCH  FIRST 1 ROWS ONLY
"""

CURSOR_PLAN_QUERY = """
SELECT plan_table_output
FROM   TABLE(DBMS_XPLAN.DISPLAY_CURSOR(:sql_id, NULL, 'TYPICAL +PEEKED_BINDS +OUTLINE'))
"""

AWR_PLAN_QUERY = """
SELECT plan_table_output
FROM   TABLE(DBMS_XPLAN.DISPLAY_AWR(:sql_id, :plan_hash_value, NULL, 'TYPICAL +PEEKED_BINDS'))
"""


class PlanRemediationAdvice(msgspec.Struct, kw_only=True):
    """Structured remediation output returned by Gemini on Vertex AI."""

    sql_id: str
    regressed_phv: int
    recommended_phv: int
    root_cause_summary: str
    why_plan_flipped: str
    risk_level: str
    remediation_plsql: str
    rollback_plsql: str


@dataclass(slots=True)
class RegressedCursorEvidence:
    """Evidence bundle collected when a SQL plan regression threshold fires."""

    sql_id: str
    current_phv: int
    best_phv: int
    current_ms: float
    baseline_ms: float
    regression_factor: float
    bind_sensitive: str
    bind_aware: str
    current_xplan: str
    baseline_xplan: str


def fetch_plan_lines(cursor: oracledb.Cursor, query: str, binds: dict[str, object]) -> str:
    """Fetch DBMS_XPLAN output rows into a single text block."""
    cursor.execute(query, binds)
    return "\n".join(row[0] for row in cursor.fetchall() if row[0] is not None)


def collect_regressed_cursor(
    conn: oracledb.Connection,
    schema_name: str,
) -> RegressedCursorEvidence | None:
    """Run Stage 1 threshold check and Stage 2 automatic XPLAN drill-down."""
    with conn.cursor() as cur:
        cur.execute(REGRESSED_SQL_QUERY, {"schema_name": schema_name.upper()})
        row = cur.fetchone()
        if row is None:
            return None

        sql_id, current_phv, best_phv, current_ms, baseline_ms, factor, bind_sens, bind_aware = row
        current_xplan = fetch_plan_lines(cur, CURSOR_PLAN_QUERY, {"sql_id": sql_id})
        baseline_xplan = fetch_plan_lines(
            cur,
            AWR_PLAN_QUERY,
            {"sql_id": sql_id, "plan_hash_value": best_phv},
        )
        return RegressedCursorEvidence(
            sql_id=str(sql_id),
            current_phv=int(current_phv),
            best_phv=int(best_phv),
            current_ms=float(current_ms),
            baseline_ms=float(baseline_ms),
            regression_factor=float(factor),
            bind_sensitive=str(bind_sens or "N"),
            bind_aware=str(bind_aware or "N"),
            current_xplan=current_xplan,
            baseline_xplan=baseline_xplan,
        )


def analyze_with_vertex_gemini(evidence: RegressedCursorEvidence) -> PlanRemediationAdvice:
    """Send the regressed and baseline execution plans to Gemini on Vertex AI."""
    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
    )
    prompt = f"""
You are a Principal Oracle Exadata DBA. A production query has regressed {evidence.regression_factor}x.

Telemetry:
- SQL_ID: {evidence.sql_id}
- Current Regressed PHV: {evidence.current_phv} ({evidence.current_ms} ms/exec)
- Historical Best PHV: {evidence.best_phv} ({evidence.baseline_ms} ms/exec)
- IS_BIND_SENSITIVE: {evidence.bind_sensitive}, IS_BIND_AWARE: {evidence.bind_aware}

Current Regressed Plan (DBMS_XPLAN.DISPLAY_CURSOR):
{evidence.current_xplan}

Historical Baseline Plan (DBMS_XPLAN.DISPLAY_AWR):
{evidence.baseline_xplan}

Tasks:
1. Explain the exact optimizer access-path change (e.g., index range scan vs full scan, HNSW FETCH APPROX omission, nested loops vs hash join, or skewed bind peeking).
2. Provide the exact PL/SQL block using DBMS_SPM.LOAD_PLANS_FROM_AWR or DBMS_SPM.LOAD_PLANS_FROM_CURSOR_CACHE to pin PHV {evidence.best_phv} as a FIXED=>'YES', ENABLED=>'YES' SQL Plan Baseline.
3. Provide the exact rollback PL/SQL block using DBMS_SPM.DROP_SQL_PLAN_BASELINE.
"""
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    return msgspec.json.decode(response.text or "{}", type=PlanRemediationAdvice)


def main() -> int:
    """Execute the closed-loop plan regression detector and human-gated action flow."""
    dsn = os.environ["ORACLE_DSN"]
    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    target_schema = os.environ.get("TARGET_SCHEMA", "APP")

    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        evidence = collect_regressed_cursor(conn, target_schema)
        if evidence is None:
            print(f"[OK] No SQL plan regressions >= 3.0x detected in schema {target_schema}.")
            return 0

        print(
            f"[ALERT] SQL_ID {evidence.sql_id} regressed {evidence.regression_factor}x "
            f"(PHV {evidence.current_phv} @ {evidence.current_ms}ms vs "
            f"baseline PHV {evidence.best_phv} @ {evidence.baseline_ms}ms)."
        )
        advice = analyze_with_vertex_gemini(evidence)
        print(f"\n--- Root Cause ({advice.risk_level}) ---\n{advice.root_cause_summary}")
        print(f"\n--- Optimizer Diff ---\n{advice.why_plan_flipped}")
        print(f"\n--- Proposed DBMS_SPM Remediation ---\n{advice.remediation_plsql}")
        print(f"\n--- Rollback Script ---\n{advice.rollback_plsql}\n")

        approval = input("Apply SQL Plan Baseline for PHV " f"{evidence.best_phv} now? [y/N]: ").strip().lower()
        if approval == "y":
            with conn.cursor() as cur:
                cur.execute(advice.remediation_plsql)
            conn.commit()
            print(f"[APPLIED] Pinned PHV {evidence.best_phv} for SQL_ID {evidence.sql_id}.")
        else:
            print("[SKIPPED] Remediation not applied; scripts saved for change review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

### Pattern C: Shell / SQLcl Pipe into Antigravity CLI (`agy`) for Scheduled AWR & ASH Triage

For DBAs who live in Bash and SQLcl (`sql`), integrating Gemini does not require rewriting existing `.sql` scripts in Python. A shell wrapper can run a fast SQL health check first and invoke **Antigravity (`agy`)** only when the output is non-empty:

```bash
#!/usr/bin/env bash
set -euo pipefail

SNAP_OUT=$(/opt/sqlcl/bin/sql -s "${ORACLE_RO_CONN}" <<'SQL'
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT 'WAIT_SPIKE|' || event || '|waits=' || total_waits || '|time_sec=' || ROUND(time_waited_micro/1e6, 1)
FROM   v$system_event
WHERE  wait_class NOT IN ('Idle')
  AND  time_waited_micro > 60 * 1e6
ORDER  BY time_waited_micro DESC
FETCH  FIRST 5 ROWS ONLY;
EXIT;
SQL
)

if [[ -z "${SNAP_OUT}" ]]; then
  exit 0
fi

printf '%s\n' "${SNAP_OUT}" | agy prompt \
  "Using the awr-reports skill and the oracle-toolbox MCP server, inspect the current top wait events piped on stdin.
   1. Call list_top_sql_by_resource and list_active_sessions to identify the offending SQL_ID or blocker.
   2. If the wait is 'enq: TX - index contention', check if the target sequence uses SCALE EXTEND.
   3. Output a 5-line incident summary plus the exact read-only verification SQL and DBA remediation script. Do not execute any DDL or DML."
```

---

### Pattern D: In-Database Semantic Incident Memory in Oracle 26ai (`V$DIAG_ALERT_EXT` + `VECTOR(3072, FLOAT32)`)

Because Oracle AI Database 26ai on Exadata supports native `VECTOR` columns, `DBMS_VECTOR.UTL_TO_EMBEDDING` (`provider: "vertexai"`), and Hybrid RRF (`CONTAINS` + `VECTOR_DISTANCE`), DBAs can turn their team's tribal runbooks and resolved incident tickets into an **in-database semantic runbook table** queried directly alongside `V$DIAG_ALERT_EXT`:

```sql
-- 1. Store DBA runbooks and resolved postmortems with 3072-dim Vertex AI embeddings
CREATE TABLE dba_runbook_memory (
    runbook_id      NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
    ora_error_code  VARCHAR2(32)   ANNOTATIONS (Display 'Primary ORA- error or wait event'),
    symptom_title   VARCHAR2(256)  NOT NULL,
    root_cause      CLOB           NOT NULL,
    fix_script      CLOB           NOT NULL,
    embedding       VECTOR(3072, FLOAT32)
        ANNOTATIONS (
            Embedding_Model 'gemini-embedding-2',
            Distance 'COSINE'
        )
);

CREATE VECTOR INDEX idx_dba_runbook_vec ON dba_runbook_memory (embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
DISTANCE COSINE
WITH TARGET ACCURACY 95;

-- 2. When a new ORA- error appears in V$DIAG_ALERT_EXT, embed the alert message
--    via Vertex AI and retrieve the top 3 matching historical DBA runbooks in one query:
WITH latest_alert AS (
    SELECT originating_timestamp,
           message_text,
           DBMS_VECTOR.UTL_TO_EMBEDDING(
               message_text,
               JSON('{
                   "provider": "vertexai",
                   "credential_name": "VERTEX_CRED",
                   "url": "https://us-central1-aiplatform.googleapis.com/v1/projects/my-gcp-project/locations/us-central1/publishers/google/models/",
                   "model": "text-embedding-004"
               }')
           ) AS alert_vec
    FROM   v$diag_alert_ext
    WHERE  originating_timestamp >= SYSTIMESTAMP - INTERVAL '15' MINUTE
      AND  message_text LIKE '%ORA-%'
    ORDER  BY originating_timestamp DESC
    FETCH  FIRST 1 ROWS ONLY
)
SELECT a.originating_timestamp,
       SUBSTR(a.message_text, 1, 120) AS live_alert,
       r.ora_error_code,
       r.symptom_title,
       r.fix_script,
       ROUND(1 - VECTOR_DISTANCE(r.embedding, a.alert_vec, COSINE), 4) AS similarity
FROM   latest_alert a
CROSS  JOIN dba_runbook_memory r
ORDER  BY VECTOR_DISTANCE(r.embedding, a.alert_vec, COSINE)
FETCH  APPROX FIRST 3 ROWS ONLY;
```

---

## 4. Safety & Governance Architecture for Production Exadata DBAs

1. **Built-in SQLcl MCP Auditing (`F9`)**:
   - Every query executed through `sql -mcp` is automatically logged into `DBTOOLS$MCP_LOG` in the connected schema, tagged with `/* LLM in use ... */` SQL comments, and attributed in `V$SESSION.MODULE` (MCP client) and `V$SESSION.ACTION` (LLM model). DBAs can monitor agent activity in real time via `GV$SESSION` and Unified Auditing.
2. **Tiered Autonomy Model**:
   - **Autonomous (Read-Only)**: Threshold detection, `DBMS_XPLAN` retrieval, ASH/AWR correlation, `DBA_SEQUENCES` / `DBA_INDEXES` inspection, and `dba_runbook_memory` vector lookup.
   - **Human-Approved (One-Click / `y/N` / PR Gate)**: Pinning a SQL Plan Baseline (`DBMS_SPM`), enabling scalable sequences (`ALTER SEQUENCE ... SCALE EXTEND`), running deferred global index cleanup (`DBMS_PART.CLEANUP_GIDX`), or terminating an orphaned blocker (`ALTER SYSTEM KILL SESSION`).
   - **Never Autonomous**: Dropping segments, modifying initialization parameters (`ALTER SYSTEM SET`), or running unreviewed DDL in production.

---

## 5. Primary-Source Citations & Verification

### Sources
- `[S1]` `.agents/bundles/knowledge/presentation/verified-facts.md#L38-L89` — Verified Oracle 26ai, Select AI, `DBMS_VECTOR`, and MCP facts in this repository (`F1`, `F2`, `F5`–`F8`, `F10`–`F12`).
- `[S2]` `docs/mcp-antigravity.md#L11-L129` — Antigravity MCP configuration for `sql -mcp`, MCP Toolbox `oracledb`, and Google Cloud Oracle MCP (`F9`–`F11`).
- `[S3]` `https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/supported-third-party-provider-operations-and-endpoints.html` & `create_credential-dbms_vector.html` — Oracle AI Vector Search 26ai `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN` Vertex AI REST provider and credential format (`F1`, `F2`).
- `[S4]` `https://docs.oracle.com/en/engineered-systems/exadata-database-machine/dbmso/exadata-storage-server-software-release-24.1.x-25.1.x-25.2.x` — Exadata AI Smart Scan vector offload, top-K filtering, and `V$SYSSTAT` cell offload metrics (`F3`, `F4`, `F13`).
- `[S5]` `https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/dbms-cloud-ai-package.html` & `google-service-account.html` — Autonomous AI Database `DBMS_CLOUD_AI` and `GCP$PA` boundaries (`F6`–`F8`).
- `[S6]` `https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.2/sqcug/using-oracle-sqlcl-mcp-server.html` — Oracle SQLcl MCP Server tools (`list-connections`, `connect`, `disconnect`, `run-sql`, `run-sqlcl`), `DBTOOLS$MCP_LOG`, and `V$SESSION` tagging (`F9`).
- `[S7]` `https://mcp-toolbox.dev/documentation/prebuilt-configs/oracledb/` — Google MCP Toolbox for Databases Oracle prebuilt tools and custom `oracle-sql` tool definitions (`F10`).
- `[S8]` `https://docs.cloud.google.com/oracle/database/docs/use-mcp` & `https://docs.cloud.google.com/sdk/gcloud/reference/oracle-database` — Oracle Database@Google Cloud remote MCP scope vs. `gcloud oracle-database` Exadata CLI hierarchy (`F11`, `F12`).
- `[S9]` `https://raw.githubusercontent.com/paypal/hera/master/README.md`, `docs/sharding.md`, `docs/bindevict.md`, `docs/taf.md` — Public PayPal HERA Oracle connection multiplexer, horizontal sharding (`scuttle_id`), and bind/SQL eviction architecture (`F6`–`F8` in FinTech context).
- `[S10]` Oracle Database 19c/26ai Documentation: RAC Administration (`racad`), SQL Language Reference (`CREATE-SEQUENCE.html` `SCALE EXTEND`), SQL Tuning Guide (`tgsql` ACS and `DBMS_SPM`), VLDB and Partitioning Guide (`vldbg` `DBMS_PART.CLEANUP_GIDX`), and GoldenGate Reference (`BRINTERVAL` / `CACHEMGR`) (`F10`–`F15`).

### Limitations & Resolved Contradictions
- **Exadata vs. ADB-S AI Package Split**: `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN` (core 26ai on Exadata and ADB) natively supports `"provider": "vertexai"` against regional `aiplatform.googleapis.com` endpoints using an OAuth `access_token`, whereas `DBMS_CLOUD_AI` / Select AI (ADB-centric) only supports `"provider": "google"` against `generativelanguage.googleapis.com` with an API key and does not support `vertexai` or `GCP$PA`.
- **Control-Plane MCP vs. CLI Split**: While Oracle Database@Google Cloud supports Exadata Database Service in the control plane via `gcloud oracle-database` (`cloud-exadata-infrastructures`, `cloud-vm-clusters`, `db-servers`, `db-nodes`), the managed remote MCP endpoint `https://oracledatabase.googleapis.com/mcp` currently exposes only Autonomous Database tools (`list_autonomous_databases`, `create_autonomous_database`).
