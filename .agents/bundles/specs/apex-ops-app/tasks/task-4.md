---
type: Task
id: apex-ops-app:task-4
flow_id: apex-ops-app
state: blocked
title: Wire REST Source Catalog entries to filtered OpenAPI artifact
description: Wire REST Source Catalog in APEXlang. Blocked on local APEX 26.1 WWV_WEBSRC_MODULE_RSERVER_FK rollback.
verification_strategy: integration_acceptance
depends_on:
  - apex-ops-app:task-3
blocked_reason: "Local APEX 26.1 rolls back import with WWV_WEBSRC_MODULE_RSERVER_FK when REST Data Sources reference a restDataSourceServer; paused by adb-free-swap."
unblock_condition: "Resume after adb-free-swap or an Oracle APEX 26.1.x patch / App Builder round-trip resolves WWV_WEBSRC_MODULE_RSERVER_FK."
commit: null
created_at: 2026-06-23T00:00:00Z
updated_at: 2026-10-13T19:15:00Z
tags:
  - task
  - apex
---

# Task task-4: Wire REST Source Catalog entries to filtered OpenAPI artifact

## Objective
Wire REST Source Catalog in APEXlang. Blocked on local APEX 26.1 WWV_WEBSRC_MODULE_RSERVER_FK rollback.

## Acceptance Criteria
- [!] Implementation complete and verified.

## Verification Strategy: integration_acceptance
Verification recorded in flow learnings and spec notes.
