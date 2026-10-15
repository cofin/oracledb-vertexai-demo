# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""MCP and A2A protocol configuration builders."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar_mcp import MCPConfig, MCPSkillsConfig
from litestar_security import mechanism, public, required

from app.domain.ai.mcp import CoffeePromptController, CoffeeSkillController

if TYPE_CHECKING:
    from app.lib.settings import Settings

__all__ = ("build_mcp_config", "build_mcp_route_opt")


def build_mcp_route_opt(settings: Settings) -> dict[str, Any]:
    """Build the route_opt dictionary for MCP and A2A protocol endpoints.

    Args:
        settings: Resolved application settings instance.

    Returns:
        Route options dictionary configuring authentication policy and CSRF exemption.
    """
    expected_key = (settings.app.MCP_API_KEY or "").strip()
    auth_policy = required(mechanism("api-key")) if expected_key else public()
    return {"auth": auth_policy, "exclude_from_csrf": True}


def build_mcp_config(settings: Settings) -> MCPConfig:
    """Build the LitestarMCP configuration with prompt/skill controllers and route auth.

    Args:
        settings: Resolved application settings instance.

    Returns:
        Configured MCPConfig instance for LitestarMCP.
    """
    skill_paths = [p for p in (Path(".agents/skills"), Path("skills")) if p.is_dir()]
    skills_config = MCPSkillsConfig(paths=skill_paths, directory_read=True) if skill_paths else None
    return MCPConfig(
        name="Cymbal Coffee MCP",
        instructions="Exposes coffee product catalog, hybrid vector+lexical search, store inventory, prompts, and skills.",
        skills=skills_config,
        prompt_controllers=(CoffeePromptController,),
        skill_controllers=(CoffeeSkillController,),
        route_opt=build_mcp_route_opt(settings),
    )
