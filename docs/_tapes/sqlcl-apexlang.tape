# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

Output docs/_static/demos/sqlcl-apexlang.mp4
Output docs/_static/demos/sqlcl-apexlang.gif

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

Type "sql -S /nolog"
Enter
Wait+Screen@30s /SQL>/
Sleep 1s

Type "apex validate -input src/apex/cymbal-coffee-ops"
Enter
Wait+Screen@60s /Valid/
Sleep 2s

Type "connect app/SuperSecret1@myatp_low"
Enter
Wait+Screen@30s /Connected/
Sleep 1s

Type "apex import -input src/apex/cymbal-coffee-ops -workspace COFFEE -schema APP -id 100"
Enter
Wait+Screen@90s /Import/
Sleep 2s

Type "apex export -applicationid 100 -exptype APEXLANG -dir src/apex -force"
Enter
Wait+Screen@90s /Export/
Sleep 2s

Type "exit"
Enter
Sleep 1s
