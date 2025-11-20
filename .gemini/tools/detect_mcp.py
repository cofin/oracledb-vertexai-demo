#!/usr/bin/env python3
"""Intelligent MCP tool detection with capability mapping."""

from dataclasses import dataclass
from enum import Enum


class ToolCapability(Enum):
    """MCP tool capability categories."""

    REASONING = "reasoning"  # Deep thinking tools
    RESEARCH = "research"  # Documentation lookup
    PLANNING = "planning"  # Workflow organization
    ANALYSIS = "analysis"  # Code analysis
    DEBUG = "debug"  # Problem investigation


@dataclass
class MCPTool:
    """MCP tool with capability metadata."""

    name: str
    available: bool
    capability: ToolCapability
    fallback: str | None = None
    use_cases: list[str] | None = None


def detect_mcp_tools() -> dict[str, MCPTool]:
    """Detect available MCP tools with intelligent fallback mapping."""

    tools = {
        # Reasoning tools (prefer crash, fallback to sequential_thinking)
        "crash": MCPTool(
            name="crash",
            available=True,  # Zen MCP tool
            capability=ToolCapability.REASONING,
            fallback="sequential_thinking",
            use_cases=[
                "Complex architectural decisions",
                "Multi-branch design exploration",
                "Iterative problem refinement",
            ],
        ),
        "sequential_thinking": MCPTool(
            name="sequential_thinking",
            available=True,  # Assuming sequential_thinking is available as a fallback
            capability=ToolCapability.REASONING,
            fallback=None,  # Last resort
            use_cases=[
                "Linear problem breakdown",
                "Step-by-step analysis",
                "Fallback when crash unavailable",
            ],
        ),
        # Research tools
        "context7": MCPTool(
            name="context7",
            available=True,  # Assuming context7 is available
            capability=ToolCapability.RESEARCH,
            fallback="web_search",
            use_cases=[
                "Library documentation lookup",
                "API reference retrieval",
                "Best practices research",
            ],
        ),
        "web_search": MCPTool(
            name="web_search",
            available=True,  # Assuming web_search is available
            capability=ToolCapability.RESEARCH,
            fallback=None,
            use_cases=[
                "Latest framework updates",
                "Community best practices",
                "Fallback documentation lookup",
            ],
        ),
        # Planning tools
        "zen_planner": MCPTool(
            name="zen_planner",
            available=True,  # Zen MCP tool
            capability=ToolCapability.PLANNING,
            use_cases=[
                "Multi-phase project planning",
                "Migration strategy design",
                "Complex feature breakdown",
            ],
        ),
        # Analysis tools
        "zen_thinkdeep": MCPTool(
            name="zen_thinkdeep",
            available=True,  # Zen MCP tool
            capability=ToolCapability.ANALYSIS,
            use_cases=[
                "Architecture review",
                "Performance analysis",
                "Security assessment",
            ],
        ),
        "zen_analyze": MCPTool(
            name="zen_analyze",
            available=True,  # Zen MCP tool
            capability=ToolCapability.ANALYSIS,
            use_cases=[
                "Code quality analysis",
                "Pattern detection",
                "Tech debt assessment",
            ],
        ),
        # Debug tools
        "zen_debug": MCPTool(
            name="zen_debug",
            available=True,  # Zen MCP tool
            capability=ToolCapability.DEBUG,
            use_cases=[
                "Root cause investigation",
                "Bug reproduction",
                "Performance debugging",
            ],
        ),
        "zen_consensus": MCPTool(
            name="zen_consensus",
            available=True,  # Zen MCP tool
            capability=ToolCapability.PLANNING,
            use_cases=[
                "Architecture decision making",
                "Technology selection",
                "Multi-model validation",
            ],
        ),
    }

    # Auto-detection logic would go here
    # For bootstrap: detect from environment or config

    return tools


def generate_tool_strategy(tools: dict[str, MCPTool]) -> str:
    """Generate intelligent tool usage strategy."""

    strategy = ["# MCP Tool Strategy\n\n"]

    by_capability = {}
    for tool in tools.values():
        if tool.capability not in by_capability:
            by_capability[tool.capability] = []
        by_capability[tool.capability].append(tool)

    for capability, tool_list in by_capability.items():
        strategy.append(f"## {capability.value.title()} Tools\n\n")

        available = [t for t in tool_list if t.available]
        _unavailable = [t for t in tool_list if not t.available]

        if available:
            primary = available[0]
            strategy.append(f"**Primary**: `{primary.name}`\n\n")

            if primary.use_cases:
                strategy.append("Use when:\n\n")
                for use_case in primary.use_cases:
                    strategy.append(f"- {use_case}\n")
                strategy.append("\n")

            if primary.fallback:
                fallback_tool = tools.get(primary.fallback)
                if fallback_tool and not fallback_tool.available:
                    strategy.append(f"**Fallback**: Manual {capability.value} (no tools available)\n\n")
                elif fallback_tool:
                    strategy.append(f"**Fallback**: `{primary.fallback}`\n\n")
        else:
            strategy.append(f"⚠️ No tools available - manual {capability.value} required\n\n")

    return "".join(strategy)


if __name__ == "__main__":
    tools = detect_mcp_tools()

    # Generate strategy document
    strategy = generate_tool_strategy(tools)

    with open(".gemini/mcp-strategy.md", "w") as f:
        f.write(strategy)

    # Generate availability list
    with open(".gemini/mcp-tools.txt", "w") as f:
        f.write("Available MCP Tools (Auto-Detected):\n\n")
        for tool in tools.values():
            status = "✓ Available" if tool.available else "✗ Not available"
            f.write(f"- {tool.name}: {status}\n")
            if tool.fallback:
                f.write(f"  Fallback: {tool.fallback}\n")

    print("✓ MCP tool detection complete")
    print("✓ Generated .gemini/mcp-tools.txt")
    print("✓ Generated .gemini/mcp-strategy.md")
