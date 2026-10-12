# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""MCP and A2A server configuration exports."""

from app.server.mcp._config import build_mcp_config, build_mcp_route_opt

__all__ = ("build_mcp_config", "build_mcp_route_opt")
