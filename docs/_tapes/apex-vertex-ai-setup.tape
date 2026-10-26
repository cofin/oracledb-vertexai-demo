# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

Output docs/_static/demos/apex-vertex-ai-setup.mp4
Output docs/_static/demos/apex-vertex-ai-setup.gif

Require uv

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

Type "uv run python manage.py infra apex status"
Enter
Wait+Screen@30s /APEX Release:/
Sleep 2s

Type "uv run python manage.py infra apex configure-vertex --mode direct --verify"
Enter
Wait+Screen@60s /APEX_AI\.GENERATE verified/
Sleep 3s
