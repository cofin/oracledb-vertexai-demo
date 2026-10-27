# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

Output docs/_static/demos/sqlcl-vertex-ai-native.mp4
Output docs/_static/demos/sqlcl-vertex-ai-native.gif

Require sql

Set Shell "bash"
Set Theme "Catppuccin Mocha"
Set Width 1200
Set Height 675
Set FontSize 18
Set Padding 20
Set TypingSpeed 45ms

Hide
Type "export PS1='$ '"
Enter
Type "clear"
Enter
Sleep 500ms
Show

Type "sql admin/SuperSecret1@myatp_low"
Enter
Wait+Screen@30s /SQL>/
Sleep 1s

Type "@src/app/db/sql/deploy/configure-vertex-ai.sql"
Enter
Wait+Screen@60s /Configured APEX_CREDENTIAL/
Sleep 2s

Type "SET SERVEROUTPUT ON;"
Enter
Wait+Screen@10s /SQL>/
Sleep 500ms

Type "DECLARE v_out CLOB; BEGIN APEX_UTIL.SET_WORKSPACE('COFFEE'); v_out := APEX_AI.GENERATE('Recommend a bold specialty dark roast.', p_service_static_id => 'COFFEE_VERTEX_AI'); DBMS_OUTPUT.PUT_LINE(v_out); END;"
Enter
Type "/"
Enter
Wait+Screen@60s /PL\/SQL procedure successfully completed/
Sleep 3s

Type "exit"
Enter
Sleep 1s
