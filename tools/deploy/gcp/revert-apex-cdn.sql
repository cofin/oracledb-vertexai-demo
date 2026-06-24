-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- revert-apex-cdn.sql
-- Reverts APEX to use local images (/i/) instead of CDN.
-- Useful for local offline development.

SET SERVEROUTPUT ON;
SET DEFINE OFF;

DECLARE
    v_con_name VARCHAR2(128);
    v_current_prefix VARCHAR2(255);
    v_target_prefix CONSTANT VARCHAR2(255) := '/i/';
BEGIN
    -- 1. Ensure we are in the correct pluggable database if connected via CDB$ROOT
    SELECT sys_context('USERENV', 'CON_NAME') INTO v_con_name FROM dual;
    IF v_con_name = 'CDB$ROOT' THEN
        EXECUTE IMMEDIATE 'ALTER SESSION SET CONTAINER = FREEPDB1';
    END IF;

    -- 2. Retrieve current parameter value dynamically to prevent compilation errors in CDB$ROOT
    EXECUTE IMMEDIATE 'BEGIN :1 := apex_instance_admin.get_parameter(''IMAGE_PREFIX''); END;'
        USING OUT v_current_prefix;

    -- 3. Update parameter if not already pointing to target local path
    IF v_current_prefix IS NULL OR v_current_prefix != v_target_prefix THEN
        EXECUTE IMMEDIATE 'BEGIN apex_instance_admin.set_parameter(''IMAGE_PREFIX'', :1); END;'
            USING v_target_prefix;
        COMMIT;
        dbms_output.put_line('APEX IMAGE_PREFIX successfully reverted to local: ' || v_target_prefix);
    ELSE
        dbms_output.put_line('APEX IMAGE_PREFIX is already set to local. No action required.');
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        dbms_output.put_line('Error reverting APEX IMAGE_PREFIX: ' || SQLERRM);
        RAISE;
END;
/
