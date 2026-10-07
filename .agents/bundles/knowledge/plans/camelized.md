---
type: Guide
title: Camelized Wire Format Plan
description: Plan for wire serialization and camel-case schemas
tags:
  - plan
  - serialization
---

# Objective
Refactor to CamelizedBaseStruct.

# Key Files & Context
- src/py/app/domain/chat/schemas/_chat.py

# Implementation Steps
1. Add import.
2. Replace msgspec.Struct.

# Verification & Testing
1. Run mypy.
