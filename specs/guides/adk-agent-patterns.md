# Google Agent Development Kit (ADK) Patterns Guide (2025)

Comprehensive guide to building AI agents with Google's Agent Development Kit (ADK) v1.0.0+ using the latest 2025 patterns for production-ready agentic applications.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [Installation and Setup](#installation-and-setup)
- [LlmAgent (Core Pattern)](#llmagent-core-pattern)
- [Tools and Functions](#tools-and-functions)
- [Session Management](#session-management)
- [Agent Execution](#agent-execution)
- [Multi-Agent Patterns](#multi-agent-patterns)
- [Memory Integration](#memory-integration)
- [Production Deployment](#production-deployment)
- [Migration from Legacy Patterns](#migration-from-legacy-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

**Google ADK** (Agent Development Kit) is an open-source, production-ready framework for building sophisticated AI agents with:

**Key Features**:

- **LlmAgent**: LLM-powered agents with tool usage
- **Workflow Agents**: Deterministic execution patterns (Sequential, Parallel, Loop)
- **Tool Integration**: Function tools, MCP tools, memory tools
- **Session Management**: Conversation history and state
- **Multi-Agent Coordination**: Complex agent orchestration
- **Production Ready**: v1.0.0 stable release (January 2025)

**ADK Powers**:

- Google Agentspace
- Google Customer Engagement Suite (CES)
- Internal Google agent applications

**Architecture**:

```
User Query
    ↓
Runner (orchestration)
    ↓
LlmAgent (reasoning)
    ├─→ Tools (actions)
    ├─→ Memory (context)
    └─→ Session (state)
    ↓
Response
```

## Quick Reference

| Component                | Purpose                          | Example                                          |
| ------------------------ | -------------------------------- | ------------------------------------------------ |
| `LlmAgent`               | LLM-powered agent with reasoning | Dynamic tool selection                           |
| `SequentialAgent`        | Linear workflow                  | Data pipeline (extract → process → generate)     |
| `ParallelAgent`          | Concurrent execution             | Multi-source search                              |
| `LoopAgent`              | Iterative execution              | Refinement loop                                  |
| `FunctionTool`           | Wrap Python function             | `FunctionTool(func=search_products)`             |
| `MCPToolset`             | Model Context Protocol tools     | External MCP servers                             |
| `PreloadMemoryTool`      | Long-term memory recall          | Conversation history                             |
| `Runner`                 | Execute agent                    | `runner.run_async(user_id, session_id, message)` |
| `InMemorySessionService` | Dev session storage              | Local testing                                    |
| `VertexAiSessionService` | Production session storage       | Vertex AI backed                                 |

## Installation and Setup

### Installation

```bash
# Install ADK with all features
pip install "google-cloud-aiplatform[adk,agent_engines]>=1.101.0"

# For async support
pip install "nest-asyncio>=1.6.0"
```

### Basic Initialization

```python
import vertexai
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Initialize Vertex AI
vertexai.init(
    project="your-project-id",
    location="us-central1"
)

# Enable nested async (for Jupyter/Colab)
import nest_asyncio
nest_asyncio.apply()
```

## LlmAgent (Core Pattern)

**LlmAgent** is the primary agent type for building flexible, intelligent agents.

**Key Characteristics**:

- Uses LLM for reasoning and decision-making
- Non-deterministic behavior (LLM-driven)
- Dynamic tool selection
- Best for language-centric, adaptive tasks

### Basic LlmAgent

```python
from google.adk.agents import LlmAgent

agent = LlmAgent(
    model="gemini-2.5-pro",  # or gemini-2.5-flash
    name="helpful_assistant",
    instruction="You are a helpful assistant. Answer user questions clearly and concisely."
)
```

**Parameters**:

- `model`: Gemini model name (`gemini-2.5-pro`, `gemini-2.5-flash`)
- `name`: Agent identifier (used in logs)
- `instruction`: System instructions (agent behavior)
- `description`: Optional agent description
- `tools`: List of tools available to agent

### LlmAgent with Tools

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Define tools
def search_products(query: str, limit: int = 5) -> list[dict]:
    """Search for products matching the query.

    Args:
        query: Search query text
        limit: Maximum number of results

    Returns:
        List of product dictionaries with id, name, description
    """
    # Implementation
    return results

def get_product_details(product_id: int) -> dict:
    """Get detailed information about a product.

    Args:
        product_id: ID of the product

    Returns:
        Product details dictionary
    """
    # Implementation
    return details

# Create agent with tools
agent = LlmAgent(
    model="gemini-2.5-flash",
    name="product_assistant",
    instruction="""You are a helpful product assistant for Cymbal Coffee.

    Use the available tools to:
    - Search for products based on user queries
    - Get detailed information about specific products
    - Provide friendly, concise recommendations (1-3 sentences)

    Always verify information using tools before responding.""",
    tools=[
        FunctionTool(func=search_products),
        FunctionTool(func=get_product_details)
    ]
)
```

**Tool Usage Flow**:

1. User sends query
2. LlmAgent reasons about query
3. Agent decides to call tool (if needed)
4. Tool executes and returns result
5. Agent incorporates result into response

### Advanced Instructions

```python
agent = LlmAgent(
    model="gemini-2.5-pro",
    name="advanced_assistant",
    instruction="""You are an expert coffee consultant.

    # Your Role
    Provide personalized coffee recommendations based on user preferences.

    # Guidelines
    - Ask clarifying questions if needed
    - Use search_products to find relevant options
    - Consider user's taste preferences (flavor notes, roast level)
    - Limit recommendations to 2-3 products max
    - Be conversational and friendly

    # Response Format
    Keep responses short (1-3 sentences) unless user asks for details.
    Example: "Based on your preference for bright, fruity flavors, I recommend
    Ethiopian Yirgacheffe. It has floral notes with hints of bergamot."

    # Tool Usage
    - search_products: Find products matching description
    - get_product_details: Get full product information

    Always use tools before making recommendations.""",
    tools=[
        FunctionTool(func=search_products),
        FunctionTool(func=get_product_details)
    ]
)
```

## Tools and Functions

### Function Tools

Wrap Python functions as agent tools:

```python
from google.adk.tools import FunctionTool
from typing import Optional

def search_with_filters(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
) -> list[dict]:
    """Search products with optional filters.

    Args:
        query: Search query text
        category: Optional category filter (e.g., "coffee", "tea")
        min_price: Minimum price filter
        max_price: Maximum price filter

    Returns:
        List of matching products
    """
    # Implementation with filters
    return filtered_results

# Wrap as tool
search_tool = FunctionTool(func=search_with_filters)

# Use in agent
agent = LlmAgent(
    model="gemini-2.5-flash",
    tools=[search_tool]
)
```

**Function Tool Requirements**:

- ✅ Type hints on all parameters
- ✅ Docstring with Args and Returns sections
- ✅ Clear, descriptive function name
- ✅ Return values (not None)

### Async Function Tools

Support async functions:

```python
import asyncio
from google.adk.tools import FunctionTool

async def async_search_products(query: str) -> list[dict]:
    """Asynchronously search for products.

    Args:
        query: Search query text

    Returns:
        List of products
    """
    # Async implementation
    results = await some_async_operation()
    return results

# Async tool
async_tool = FunctionTool(func=async_search_products)

agent = LlmAgent(
    model="gemini-2.5-flash",
    tools=[async_tool]
)
```

### MCP Tools (Model Context Protocol)

Connect to external MCP servers:

```python
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
    StdioConnectionParams
)

# Connect to MCP server
mcp_tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="mcp-server-name",
            args=["--option", "value"]
        )
    )
)

# Use MCP tools in agent
agent = LlmAgent(
    model="gemini-2.5-pro",
    name="mcp_assistant",
    instruction="Use MCP tools to access external data sources.",
    tools=[mcp_tools]
)
```

**MCP Use Cases**:

- External APIs (weather, news, databases)
- Third-party services
- Custom data sources
- Pre-built MCP servers

#### Database Interaction with `sqlcl` MCP Server

A powerful use case for MCP tools is interacting with databases. This project includes an MCP server for Oracle Database using `sqlcl`.

While you can create a generic `MCPToolset` for `sqlcl`, it is **highly recommended** that you follow the best practices outlined in the **[Oracle SQLcl Usage Guide](sqlcl-usage-guide.md#best-practices-for-ai-agent-interaction-with-the-sqlcl-mcp-server)** to ensure safe and efficient database interactions.

This guide provides detailed information on:

- **Agent Prompting:** How to write effective prompts for database queries.
- **Tool Selection:** How to choose the right MCP tool for your task.
- **Avoiding Pitfalls:** How to avoid common issues like loops and data overload.
- **Caching Strategies:** How to improve performance with application-level and database-level caching.

**Example `MCPToolset` for `sqlcl`:**

```python
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
    StdioConnectionParams
)

# Connect to the sqlcl MCP server
sqlcl_mcp_tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="sql",
            args=["-mcp"]
        )
    )
)

# Use sqlcl MCP tools in an agent
agent = LlmAgent(
    model="gemini-2.5-pro",
    name="database_assistant",
    instruction="Use the available tools to answer questions about the Oracle database. Refer to the SQLcl Usage Guide for best practices.",
    tools=[sqlcl_mcp_tools]
)
```

### Tool Best Practices

1. **Clear Docstrings**:

```python
def good_tool(query: str, limit: int) -> list[dict]:
    """Search products with semantic similarity.

    Args:
        query: User's search query in natural language
        limit: Maximum number of results to return (1-20)

    Returns:
        List of product dictionaries, each containing:
        - id: Product ID (int)
        - name: Product name (str)
        - description: Product description (str)
        - price: Price in USD (float)
    """
    pass
```

2. **Type Safety**:

```python
from typing import List, Dict, Optional

def typed_tool(
    required_param: str,
    optional_param: Optional[int] = None
) -> List[Dict[str, any]]:
    """Well-typed tool function."""
    pass
```

3. **Error Handling**:

```python
def robust_tool(product_id: int) -> dict:
    """Get product details with error handling.

    Args:
        product_id: Product ID

    Returns:
        Product details or error dict
    """
    try:
        product = fetch_product(product_id)
        return product
    except ProductNotFound:
        return {"error": f"Product {product_id} not found"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
```

## Session Management

### InMemorySessionService (Development)

Local session storage for testing:

```python
from google.adk.sessions import InMemorySessionService

# Create session service
session_service = InMemorySessionService()

# Create session
session = await session_service.create_session(
    app_name="coffee_assistant",
    user_id="user_123",
    session_id="session_456"  # Optional, auto-generated if not provided
)

print(f"Session ID: {session.id}")
print(f"Created: {session.created_at}")
```

### VertexAiSessionService (Production)

Production-grade session storage:

```python
from google.adk.sessions import VertexAiSessionService
from vertexai import agent_engines

# Create Agent Engine (one-time setup)
agent_engine = agent_engines.AgentEngine.create(
    display_name="coffee_assistant_engine",
    location="us-central1"
)

# Session service
session_service = VertexAiSessionService(
    project="your-project-id",
    location="us-central1",
    agent_engine_id=agent_engine.name
)

# Create session
session = await session_service.create_session(
    app_name="coffee_assistant",
    user_id="user_123"
)
```

**VertexAiSessionService Benefits**:

- Persistent storage (survives restarts)
- Multi-instance support
- Automatic cleanup
- Production reliability

### Session Lifecycle

```python
# Create session
session = await session_service.create_session(
    app_name="my_app",
    user_id="user_123"
)

# List user sessions
sessions = await session_service.list_sessions(
    app_name="my_app",
    user_id="user_123"
)

# Get specific session
session = await session_service.get_session(
    app_name="my_app",
    user_id="user_123",
    session_id="session_456"
)

# Delete session
await session_service.delete_session(
    app_name="my_app",
    user_id="user_123",
    session_id="session_456"
)
```

## Agent Execution

### Runner Setup

```python
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService

# Create agent
agent = LlmAgent(
    model="gemini-2.5-flash",
    name="assistant",
    instruction="You are a helpful assistant."
)

# Create session service
session_service = InMemorySessionService()

# Create runner
runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service
)
```

### Single Query Execution

```python
from google.genai import types

# Create message
content = types.Content(
    role="user",
    parts=[types.Part(text="What coffees do you recommend?")]
)

# Run agent
events = [
    event async for event in runner.run_async(
        user_id="user_123",
        session_id="session_456",
        new_message=content
    )
]

# Extract response
response_text = ""
for event in events:
    if hasattr(event, 'content') and event.content.role == "model":
        for part in event.content.parts:
            if hasattr(part, 'text'):
                response_text += part.text

print(response_text)
```

### Chat Loop (Interactive)

```python
import asyncio

async def chat_loop(runner, session_id: str, user_id: str):
    """Interactive chat loop."""
    print("Chat started. Type 'quit' to exit.")

    while True:
        # Get user input
        user_input = input("You: ")

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Goodbye!")
            break

        # Create message
        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )

        # Run agent
        print("Assistant: ", end="", flush=True)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if hasattr(event, 'content') and event.content.role == "model":
                for part in event.content.parts:
                    if hasattr(part, 'text'):
                        print(part.text, end="", flush=True)
        print()  # New line

# Start chat
session = await session_service.create_session(
    app_name="coffee_assistant",
    user_id="user_123"
)

await chat_loop(runner, session.id, "user_123")
```

### Extracting Tool Calls

```python
def extract_tool_calls(events: list) -> list[dict]:
    """Extract all tool calls from agent events."""
    tool_calls = []

    for event in events:
        if not hasattr(event, 'content'):
            continue

        for part in event.content.parts:
            if hasattr(part, 'function_call'):
                fc = part.function_call
                tool_calls.append({
                    "tool_name": fc.name,
                    "arguments": dict(fc.args)
                })

    return tool_calls

# Usage
events = [event async for event in runner.run_async(...)]
tool_calls = extract_tool_calls(events)
print(f"Agent called {len(tool_calls)} tools")
```

## Multi-Agent Patterns

### Coordinator/Dispatcher Pattern

Route queries to specialized agents:

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Specialized agents
search_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="search_specialist",
    instruction="Search for products based on user queries.",
    tools=[FunctionTool(func=search_products)]
)

analytics_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="analytics_specialist",
    instruction="Analyze product data and provide insights.",
    tools=[FunctionTool(func=get_analytics)]
)

# Coordinator agent
coordinator = LlmAgent(
    model="gemini-2.5-pro",
    name="coordinator",
    instruction="""You are a coordinator that routes user queries to specialized agents.

    Available specialists:
    - search_specialist: For product searches
    - analytics_specialist: For data analysis

    Determine which specialist to use based on the query."""
)

# Note: Implement routing logic in your application code
```

### Sequential Pipeline Pattern

Linear workflow execution:

```python
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.tools import FunctionTool

# Pipeline stages
extraction_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="data_extractor",
    instruction="Extract key information from user input.",
    tools=[FunctionTool(func=extract_data)]
)

processing_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="data_processor",
    instruction="Process extracted data.",
    tools=[FunctionTool(func=process_data)]
)

generation_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="report_generator",
    instruction="Generate final report from processed data.",
    tools=[FunctionTool(func=generate_report)]
)

# Sequential pipeline
pipeline = SequentialAgent(
    agents=[
        extraction_agent,
        processing_agent,
        generation_agent
    ]
)

# Execute pipeline
runner = Runner(
    agent=pipeline,
    app_name="data_pipeline",
    session_service=session_service
)
```

### Parallel Fan-Out Pattern

Concurrent execution:

```python
from google.adk.agents import ParallelAgent, LlmAgent

# Parallel agents
web_search_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="web_searcher",
    tools=[FunctionTool(func=web_search)]
)

db_search_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="db_searcher",
    tools=[FunctionTool(func=db_search)]
)

api_search_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="api_searcher",
    tools=[FunctionTool(func=api_search)]
)

# Parallel execution
parallel_search = ParallelAgent(
    agents=[
        web_search_agent,
        db_search_agent,
        api_search_agent
    ]
)
```

## Memory Integration

### Long-Term Memory with PreloadMemoryTool

```python
from google.adk.agents import LlmAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.memory import VertexAiMemoryBankService
from google.adk.runners import Runner

# Create memory service
memory_service = VertexAiMemoryBankService(
    project="your-project-id",
    location="us-central1",
    agent_engine_id=agent_engine.name
)

# Agent with memory tool
agent = LlmAgent(
    model="gemini-2.5-pro",
    name="memory_agent",
    instruction="""You are an assistant with perfect memory.

    Use the PreloadMemoryTool to:
    - Recall past conversations
    - Remember user preferences
    - Build upon previous knowledge

    Reference past conversations naturally when relevant.""",
    tools=[PreloadMemoryTool()]
)

# Runner with memory service
runner = Runner(
    agent=agent,
    app_name="memory_app",
    session_service=session_service,
    memory_service=memory_service  # Enable memory
)
```

**Memory automatically stores**:

- Conversation history
- User interactions
- Agent responses
- Tool usage patterns

### Memory Search

```python
# Memory service provides semantic search
memories = await memory_service.search_memory(
    query="What did the user say about coffee preferences?",
    user_id="user_123",
    top_k=5
)

for memory in memories:
    print(f"Memory: {memory.content}")
    print(f"Relevance: {memory.score}")
```

## Production Deployment

### Production-Ready Service

```python
import structlog
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import VertexAiSessionService
from google.genai import types

logger = structlog.get_logger()


class ProductAgentService:
    """Production-ready ADK agent service."""

    def __init__(
        self,
        project_id: str,
        location: str,
        agent_engine_id: str
    ):
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Session service
        self.session_service = VertexAiSessionService(
            project=project_id,
            location=location,
            agent_engine_id=agent_engine_id
        )

        # Create agent
        self.agent = LlmAgent(
            model="gemini-2.5-flash",
            name="product_assistant",
            instruction="""You are a helpful product assistant.
            Use tools to search and provide information.
            Keep responses concise and friendly.""",
            tools=[
                FunctionTool(func=self.search_products),
                FunctionTool(func=self.get_product_details)
            ]
        )

        # Create runner
        self.runner = Runner(
            agent=self.agent,
            app_name="product_assistant",
            session_service=self.session_service
        )

        logger.info("agent_service_initialized")

    async def search_products(self, query: str, limit: int = 5) -> list[dict]:
        """Search for products."""
        # Implementation
        return results

    async def get_product_details(self, product_id: int) -> dict:
        """Get product details."""
        # Implementation
        return details

    async def query(
        self,
        user_id: str,
        session_id: str,
        message: str
    ) -> tuple[str, list[dict]]:
        """
        Process user query.

        Returns:
            - response text
            - list of tool calls
        """
        try:
            # Create message
            content = types.Content(
                role="user",
                parts=[types.Part(text=message)]
            )

            # Run agent
            events = [
                event async for event in self.runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
                )
            ]

            # Extract response and tool calls
            response_text = ""
            tool_calls = []

            for event in events:
                if not hasattr(event, 'content'):
                    continue

                if event.content.role == "model":
                    for part in event.content.parts:
                        if hasattr(part, 'text'):
                            response_text += part.text
                        elif hasattr(part, 'function_call'):
                            fc = part.function_call
                            tool_calls.append({
                                "tool": fc.name,
                                "args": dict(fc.args)
                            })

            logger.info(
                "agent_query_complete",
                user_id=user_id,
                tool_count=len(tool_calls)
            )

            return response_text, tool_calls

        except Exception as e:
            logger.error("agent_query_error", error=str(e))
            raise

    async def create_session(self, user_id: str) -> str:
        """Create new session for user."""
        session = await self.session_service.create_session(
            app_name="product_assistant",
            user_id=user_id
        )
        return session.id

    async def list_user_sessions(self, user_id: str) -> list[str]:
        """List all sessions for user."""
        sessions = await self.session_service.list_sessions(
            app_name="product_assistant",
            user_id=user_id
        )
        return [s.id for s in sessions]
```

### Litestar Integration

```python
from litestar import Litestar, post
from litestar.datastructures import State
from pydantic import BaseModel


class QueryRequest(BaseModel):
    user_id: str
    session_id: str | None = None
    message: str


class QueryResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict]


@post("/api/agent/query")
async def agent_query(
    data: QueryRequest,
    state: State
) -> QueryResponse:
    """Agent query endpoint."""
    agent_service: ProductAgentService = state.agent_service

    # Create session if needed
    if not data.session_id:
        session_id = await agent_service.create_session(data.user_id)
    else:
        session_id = data.session_id

    # Query agent
    response, tool_calls = await agent_service.query(
        user_id=data.user_id,
        session_id=session_id,
        message=data.message
    )

    return QueryResponse(
        response=response,
        session_id=session_id,
        tool_calls=tool_calls
    )


def create_app() -> Litestar:
    """Create Litestar app with ADK agent."""

    async def on_startup(state: State):
        """Initialize agent service on startup."""
        state.agent_service = ProductAgentService(
            project_id=PROJECT_ID,
            location=LOCATION,
            agent_engine_id=AGENT_ENGINE_ID
        )

    return Litestar(
        route_handlers=[agent_query],
        on_startup=[on_startup]
    )
```

## Troubleshooting

### Issue: Agent Not Calling Tools

**Symptom**: Agent generates text response instead of calling tools.

**Solutions**:

1. **Improve tool docstrings**: Add clear descriptions
2. **Update instructions**: Explicitly tell agent to use tools
3. **Check function signatures**: Ensure type hints present
4. **Verify tool registration**: Tools in `tools` parameter

### Issue: Session Not Persisting

**Symptom**: Conversation history lost between requests.

**Solutions**:

1. **Use same session_id**: Reuse session ID for same conversation
2. **Check session service**: Verify `VertexAiSessionService` configured
3. **Verify Agent Engine**: Ensure Agent Engine created

### Issue: Slow Agent Responses

**Symptom**: Agent takes >5 seconds to respond.

**Solutions**:

1. **Use gemini-2.5-flash**: Faster than gemini-2.5-pro
2. **Reduce tool complexity**: Simplify tool implementations
3. **Cache tool results**: Add caching layer
4. **Limit conversation history**: Trim old messages

## See Also

- [Vertex AI Integration](vertex-ai-integration.md) - Embeddings and generation
- [Architecture Overview](architecture.md) - System design
- [Litestar Framework](litestar-framework.md) - Web framework integration

## Resources

- ADK Python: https://github.com/google/adk-python
- ADK Documentation: https://google.github.io/adk-docs/
- ADK Samples: https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini
- Agent Engine: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/develop/adk
