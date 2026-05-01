-- Copyright 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- Oracle 26ai Database Schema for Coffee Recommendation System
-- This script creates all necessary tables with Oracle 26ai features

-- Switch to the PDB (Pluggable Database)
ALTER SESSION SET CONTAINER = freepdb1;
grant select on v_$transaction to app;
GRANT CONNECT, RESOURCE TO app;
/* needed for connection pooling */
GRANT SELECT ON v_$transaction TO app;
 /* needed for vector operations */
GRANT CREATE MINING MODEL TO app;
GRANT UNLIMITED TABLESPACE TO app;
GRANT CREATE SEQUENCE TO app;
GRANT CREATE TABLE TO app;
GRANT CREATE VIEW TO app;
GRANT CREATE PROCEDURE TO app;
GRANT DB_DEVELOPER_ROLE TO app;
/
