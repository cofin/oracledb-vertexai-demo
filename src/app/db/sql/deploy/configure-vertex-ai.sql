-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- src/app/db/sql/deploy/configure-vertex-ai.sql
-- Standalone PL/SQL script for Oracle SQLcl and SQL*Plus.
-- Provisions Oracle APEX 26.1 Direct Vertex AI integration (DBMS_NETWORK_ACL_ADMIN,
-- APEX_CREDENTIAL, and COFFEE_VERTEX_AI Generative AI Service) without Python wrappers.
--
-- Usage in SQLcl / SQL*Plus:
--   sql admin/SuperSecret1@myatp_low @src/app/db/sql/deploy/configure-vertex-ai.sql "<oauth_bearer_token>" "<gcp_project_id>" ["<location>"]

SET SERVEROUTPUT ON;
SET DEFINE ON;
WHENEVER SQLERROR EXIT FAILURE ROLLBACK;

DEFINE OAUTH_TOKEN = "&1";
DEFINE GCP_PROJECT = "&2";
DEFINE GCP_LOCATION = "&3";

-- Default location to 'global' if not provided
COLUMN def_loc NEW_VALUE GCP_LOCATION NOPRINT;
SELECT CASE WHEN '&3' IS NULL OR '&3' = '' OR '&3' = '&' || '3' THEN 'global' ELSE '&3' END AS def_loc FROM dual;

DECLARE
    v_con_name      VARCHAR2(128);
    v_apex_schema   VARCHAR2(128);
    v_workspace     CONSTANT VARCHAR2(30) := 'COFFEE';
    v_app_schema    CONSTANT VARCHAR2(30) := 'APP';
    v_cred_id       CONSTANT VARCHAR2(30) := 'VERTEX_AI_CRED';
    v_service_id    CONSTANT VARCHAR2(30) := 'COFFEE_VERTEX_AI';
    v_model         CONSTANT VARCHAR2(64) := 'google/gemini-3.8-flash';
    v_base_url      VARCHAR2(512);
    v_ws_id         NUMBER;
    v_cred_count    NUMBER := 0;
    v_smoke_output  CLOB;
BEGIN
    -- 1. Pluggable database check
    SELECT sys_context('USERENV', 'CON_NAME') INTO v_con_name FROM dual;
    IF v_con_name = 'CDB$ROOT' THEN
        EXECUTE IMMEDIATE 'ALTER SESSION SET CONTAINER = FREEPDB1';
    END IF;

    -- 2. Detect active APEX engine schema (e.g. APEX_260100)
    SELECT username INTO v_apex_schema
      FROM all_users
     WHERE REGEXP_LIKE(username, '^APEX_[0-9]{6}$')
     ORDER BY username DESC
     FETCH FIRST 1 ROWS ONLY;

    dbms_output.put_line('Configuring APEX 26.1 in schema ' || v_apex_schema || ' for workspace ' || v_workspace);

    -- 3. Grant outbound network ACLs for Vertex AI endpoint
    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host       => 'aiplatform.googleapis.com',
        lower_port => 443,
        upper_port => 443,
        ace        => xs$ace_type(
            privilege_list => xs$name_list('http', 'connect'),
            principal_name => v_app_schema,
            principal_type => xs_acl.ptype_db
        )
    );

    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host       => 'aiplatform.googleapis.com',
        lower_port => 443,
        upper_port => 443,
        ace        => xs$ace_type(
            privilege_list => xs$name_list('http', 'connect'),
            principal_name => v_apex_schema,
            principal_type => xs_acl.ptype_db
        )
    );
    dbms_output.put_line('✓ Granted DBMS_NETWORK_ACL_ADMIN host ACEs for aiplatform.googleapis.com:443');

    -- 4. Set APEX Workspace Context
    v_ws_id := APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => v_workspace);
    IF v_ws_id IS NULL OR v_ws_id = 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'APEX workspace not found: ' || v_workspace);
    END IF;
    APEX_UTIL.SET_SECURITY_GROUP_ID(p_security_group_id => v_ws_id);

    -- 5. Upsert APEX_CREDENTIAL (VERTEX_AI_CRED)
    SELECT COUNT(*)
      INTO v_cred_count
      FROM apex_workspace_credentials
     WHERE workspace = v_workspace
       AND static_id = v_cred_id;

    IF v_cred_count = 0 THEN
        APEX_CREDENTIAL.CREATE_CREDENTIAL(
            p_credential_name      => 'Vertex AI OAuth2 Bearer',
            p_credential_static_id => v_cred_id,
            p_authentication_type  => APEX_CREDENTIAL.C_TYPE_HTTP_HEADER
        );
    END IF;

    APEX_CREDENTIAL.SET_PERSISTENT_CREDENTIALS(
        p_credential_static_id => v_cred_id,
        p_key                  => 'Authorization',
        p_value                => 'Bearer ' || '&OAUTH_TOKEN'
    );
    dbms_output.put_line('✓ Configured APEX_CREDENTIAL (' || v_cred_id || ') with OAuth2 Bearer token');

    -- 6. Register Generative AI Service (COFFEE_VERTEX_AI)
    v_base_url := 'https://aiplatform.googleapis.com/v1/projects/' || '&GCP_PROJECT' || '/locations/' || '&GCP_LOCATION' || '/endpoints/openapi';

    EXECUTE IMMEDIATE
        'BEGIN ' ||
        '    ' || v_apex_schema || '.wwv_flow_ai_api.create_or_replace_service( ' ||
        '        p_workspace_id       => :1, ' ||
        '        p_name               => :2, ' ||
        '        p_static_id          => :3, ' ||
        '        p_ai_provider        => ''OPENAI'', ' ||
        '        p_base_url           => :4, ' ||
        '        p_credential_id      => (SELECT credential_id FROM apex_workspace_credentials WHERE workspace = :5 AND static_id = :6), ' ||
        '        p_model_name         => :7, ' ||
        '        p_used_by_app_builder => ''Y'' ' ||
        '    ); ' ||
        'END;'
    USING v_ws_id, 'Cymbal Coffee Vertex AI', v_service_id, v_base_url, v_workspace, v_cred_id, v_model;
    dbms_output.put_line('✓ Registered Generative AI Service (' || v_service_id || ') -> ' || v_model);

    COMMIT;

    -- 7. Live verification smoke test via APEX_AI.GENERATE
    BEGIN
        v_smoke_output := APEX_AI.GENERATE(
            p_prompt            => 'Reply with a one-sentence specialty coffee greeting from Cymbal Coffee.',
            p_service_static_id => v_service_id
        );
        dbms_output.put_line('✓ APEX_AI.GENERATE smoke verification succeeded:');
        dbms_output.put_line('  "' || SUBSTR(v_smoke_output, 1, 120) || '..."');
    EXCEPTION
        WHEN OTHERS THEN
            dbms_output.put_line('! Warning: Provisioning succeeded but verification call returned: ' || SQLERRM);
    END;
END;
/
