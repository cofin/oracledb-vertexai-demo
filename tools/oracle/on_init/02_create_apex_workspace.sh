#!/bin/bash
set -e

echo "Provisioning APEX workspace 'COFFEE' with primary schema 'APP'..."

sqlplus -s / as sysdba <<EOF
ALTER SESSION SET CONTAINER = freepdb1;

DECLARE
    v_workspace_exists NUMBER;
    v_security_group_id NUMBER;
    v_user_exists NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_workspace_exists FROM apex_workspaces WHERE workspace = 'COFFEE';
    IF v_workspace_exists = 0 THEN
        apex_instance_admin.add_workspace (
            p_workspace_id   => NULL,
            p_workspace      => 'COFFEE',
            p_primary_schema => 'APP'
        );
        COMMIT;
    END IF;
    
    SELECT workspace_id INTO v_security_group_id FROM apex_workspaces WHERE workspace = 'COFFEE';
    apex_util.set_security_group_id(p_security_group_id => v_security_group_id);
    
    SELECT COUNT(*) INTO v_user_exists FROM apex_workspace_apex_users WHERE workspace_name = 'COFFEE' AND user_name = 'ADMIN';
    IF v_user_exists = 0 THEN
        apex_util.create_user(
            p_user_name                  => 'ADMIN',
            p_web_password               => '$ADMIN_PASSWORD',
            p_developer_privs            => 'ADMIN:CREATE:DATA_LOADER:EDIT:RUN:CONVERT',
            p_default_schema             => 'APP',
            p_allow_app_building_yn      => 'Y',
            p_allow_sql_workshop_yn      => 'Y',
            p_allow_team_development_yn  => 'Y'
        );
        COMMIT;
    END IF;
END;
/
EOF

echo "APEX workspace 'COFFEE' successfully provisioned."
