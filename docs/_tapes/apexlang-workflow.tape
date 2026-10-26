# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

Output docs/_static/demos/apexlang-workflow.mp4
Output docs/_static/demos/apexlang-workflow.gif

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

Type "uv run python manage.py infra apex validate --alias cymbal-coffee-ops"
Enter
Wait+Screen@60s /Validated APEXlang source/
Sleep 2s

Type "uv run python manage.py infra apex import --alias cymbal-coffee-ops"
Enter
Wait+Screen@90s /Imported APEXlang source/
Sleep 2s

Type "uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops"
Enter
Wait+Screen@90s /Exported APEXlang source/
Sleep 3s
