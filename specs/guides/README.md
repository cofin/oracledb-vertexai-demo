# Documentation Guides

> **Purpose**: Canonical documentation for the Oracle Database 23ai + Vertex AI demonstration application
> **Audience**: Developers, AI agents (Gemini, Claude Code, etc.), conference attendees
> **Maintained**: Yes - commit all changes to version control
> **Last Updated**: 2025-10-07
> **Migration Status**: ✅ Complete (SQLSpec migration successful)

## Quick Start Paths

### New Developer?

Start here to understand the system:

1. **[SQLSpec Migration](../../MIGRATION.md)** - ✅ Complete migration overview (start here!)
2. **[Architecture](./architecture.md)** - System overview, components, data flow
3. **[SQLSpec Patterns](./sqlspec-patterns.md)** - Modern database patterns
4. **[Oracle Vector Search](./oracle-vector-search.md)** - Core database vector capabilities

### Deploying the Application?

Choose your deployment path:

1. **Local Development**: [Deployment Guide](../../DEPLOYMENT.md#local-development-setup) - Docker setup
2. **Production (Autonomous)**: [Autonomous Setup](./autonomous-database-setup.md) - GCP deployment
3. **Environment Config**: [Deployment Guide](../../DEPLOYMENT.md#environment-variables) - All variables

### Adding AI Features?

Follow this path for AI/ML integration:

1. **[Vertex AI Integration](./vertex-ai-integration.md)** - Embeddings, chat models, caching
2. **[ADK Agent Patterns](./adk-agent-patterns.md)** - Google ADK orchestration
3. **[Oracle Vector Search](./oracle-vector-search.md)** - Similarity search implementation

### Performance Tuning?

Optimize database and application performance:

1. **[Oracle Performance](./oracle-performance.md)** - Database optimization parameters
2. **[Oracle Vector Search](./oracle-vector-search.md)** - Vector index tuning
3. **[SQLSpec Patterns](./sqlspec-patterns.md)** - Query optimization patterns

---

## All Guides

### Migration & Deployment (NEW)

| Guide                                                            | Description                               | Key Topics                                                         |
| ---------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------ |
| **[SQLSpec Migration](../../MIGRATION.md)** ✅                   | Complete migration from litestar-oracledb | Before/after, breaking changes, benefits, 40% code reduction       |
| **[Deployment Guide](../../DEPLOYMENT.md)** ✅                   | All deployment modes (local + autonomous) | Setup, environment vars, troubleshooting, running app              |
| **[Autonomous Database Setup](./autonomous-database-setup.md)**  | Oracle Autonomous on GCP                  | Wallet config, interactive wizard, security, tuning                |
| **[Manage CLI Guide](./manage-cli-guide.md)** ✨ NEW             | Unified DevOps CLI (manage.py)            | init, install, doctor, database, wallet, status commands           |
| **[SQLcl Usage Guide](./sqlcl-usage-guide.md)** ✨ NEW           | Oracle SQLcl command-line + MCP           | Traditional CLI, MCP server mode, AI-powered operations            |
| **[Gemini MCP Integration](./gemini-mcp-integration.md)** ✨ NEW | AI-powered database interactions          | SQLcl MCP, Sequential Thinking, Context7, natural language queries |
| **[Oracle Deployment Tools](./oracle-deployment-tools.md)**      | Low-level deployment utilities            | Container management, wallet config, SQLcl install                 |

### Database & AI

| Guide                                                   | Description                            | Key Topics                                                               |
| ------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| **[SQLSpec Patterns](./sqlspec-patterns.md)** ✅        | Modern database patterns with SQLSpec  | Service classes, sessions, parameter binding, Oracle features            |
| **[Oracle Vector Search](./oracle-vector-search.md)**   | Oracle 23ai native vector capabilities | VECTOR type, HNSW/IVFFlat indexes, similarity functions, python-oracledb |
| **[Oracle JSON](./oracle-json.md)**                     | JSON Relational Duality features       | JSON columns, constraints, duality views, performance                    |
| **[Oracle Performance](./oracle-performance.md)**       | Database tuning and optimization       | Memory parameters, vectorization, index strategies                       |
| **[Vertex AI Integration](./vertex-ai-integration.md)** | Google AI services integration         | text-embedding-004, Gemini 2.0, caching, error handling                  |

### Application Framework

| Guide                                             | Description                         | Key Topics                                                    |
| ------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------- |
| **[Litestar Framework](./litestar-framework.md)** | Async Python web framework patterns | Routing, dependency injection, HTMX, sessions, plugins        |
| **[ADK Agent Patterns](./adk-agent-patterns.md)** | Google ADK orchestration            | LlmAgent, tools, multi-agent coordination, session management |

### Architecture & Design

| Guide                                 | Description           | Key Topics                                                |
| ------------------------------------- | --------------------- | --------------------------------------------------------- |
| **[Architecture](./architecture.md)** | Overall system design | Component interaction, data flow, deployment architecture |

---

## For AI Agents

When Claude Code or other AI assistants work on this project, follow this research priority:

### Research Priority Order

1. **READ THESE GUIDES FIRST** 📚
   - They are comprehensive, maintained, and reflect current project patterns
   - Located at: `/home/cody/code/g/oracledb-vertexai-demo/docs/guides/`
   - Always check here before searching external sources

2. **Context7 SECOND** 📖
   - For library-specific API documentation
   - Use when guides reference a library but you need detailed API info
   - Example: After reading oracle-vector-search.md, check Context7 for python-oracledb specifics

3. **WebSearch LAST** 🌐
   - Only for very recent updates (2025+)
   - When guides don't cover a specific new feature
   - For bleeding-edge patterns not yet documented

### Path Conventions

Use absolute paths from repo root when referencing guides:

```python
# In agent definitions
/home/cody/code/oracledb-vertexai-demo/docs/guides/oracle-vector-search.md
```

### Agent Assignments

| Agent               | Scope                                        | Primary Guides                                                                                                                       |
| ------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **backend-expert**  | Oracle, Vertex AI, ADK, SQLSpec, caching     | oracle-vector-search.md, oracle-json.md, oracle-performance.md, vertex-ai-integration.md, adk-agent-patterns.md, sqlspec-patterns.md |
| **frontend-expert** | Litestar, HTMX, routing, sessions, templates | litestar-framework.md                                                                                                                |
| **planner**         | Task planning, parallel work coordination    | architecture.md, oracle-vector-search.md, litestar-framework.md                                                                      |

---

## For Humans

### What Makes These Guides Special

- **Code Examples from Actual Project**: All examples are real code, not hypothetical
- **Troubleshooting Sections**: Common issues and solutions included
- **Performance Benchmarks**: Real metrics where relevant
- **Cross-Referenced**: Links between related topics
- **Oracle 23ai Native**: No PostgreSQL legacy terminology

### Guide Structure

Each guide follows a consistent format:

```markdown
# Guide Title

> Context, Audience, Last Updated

## Quick Reference

[Tables with key information for fast lookup]

## Table of Contents

[Detailed sections]

## Core Concepts

[Fundamentals explained clearly]

## Implementation Patterns

[Practical patterns with code]

## Code Examples

[Real, working code from the project]

## Troubleshooting

[Common issues and solutions]

## References

[Links to external docs]
```

---

## Maintenance Guidelines

### When to Update Guides

Update guides when:

- **Patterns change** in the codebase
- **New features** are added to Oracle 23ai, Vertex AI, or ADK
- **Performance characteristics** change significantly
- **Dependencies** are upgraded (python-oracledb, Litestar, etc.)
- **Common issues** are discovered and solved

### How to Update

1. **Locate the relevant guide** in `docs/guides/`
2. **Update the content** following the existing structure
3. **Update "Last Updated" date** at the top
4. **Test code examples** to ensure they still work
5. **Update cross-references** if moving sections
6. **Commit with descriptive message**:

   ```bash
   git commit -m "docs: update oracle-vector-search for HNSW parameter tuning"
   ```

### Adding New Guides

When adding a new guide:

1. Follow the template structure (see any existing guide)
2. Include practical code examples from the project
3. Add troubleshooting section with common issues
4. Link to relevant external documentation
5. Test all code snippets work
6. Add entry to this README.md index
7. Cross-reference from related guides

---

## Common Patterns by Topic

### Vector Search

**Files**: `oracle-vector-search.md`, `vertex-ai-integration.md`, `sqlspec-patterns.md`

**Flow**: Generate embedding → Cache check → Vector similarity search → Return results

**Example**:

```python
# 1. Generate/retrieve embedding
embedding, cache_hit = await vertex_ai_service.get_text_embedding_with_cache_status(query)

# 2. Vector similarity search
products = await product_service.vector_similarity_search(
    query_embedding=embedding,
    similarity_threshold=0.7,
    limit=5
)
```

### Web Request Handling

**Files**: `litestar-framework.md`, `sqlspec-patterns.md`

**Flow**: HTTP request → Litestar routing → Dependency injection → Service layer → Database → Response

**Example**:

```python
# Litestar controller with DI
@post("/search")
async def search(
    data: SearchRequest,
    product_service: ProductService,  # DI provided
) -> list[Product]:
    return await product_service.search(data.query)
```

### Agent Orchestration

**Files**: `adk-agent-patterns.md`, `vertex-ai-integration.md`

**Flow**: User query → LlmAgent → Tool selection → Tool execution → Response

**Example**:

```python
# Define agent with tools
agent = LlmAgent(
    model="gemini-2.0-flash",
    tools=[search_products, get_product_details],
    instruction="You are a coffee shop assistant..."
)
```

---

## External Resources

### Official Documentation

- **Oracle Database 23ai**: [docs.oracle.com/database/oracle/oracle-database/23/](https://docs.oracle.com/en/database/oracle/oracle-database/23/)
- **python-oracledb**: [python-oracledb.readthedocs.io](https://python-oracledb.readthedocs.io/)
- **Vertex AI**: [cloud.google.com/vertex-ai/docs](https://cloud.google.com/vertex-ai/docs)
- **Google ADK**: [google.github.io/adk-docs/](https://google.github.io/adk-docs/)
- **Litestar**: [docs.litestar.dev/](https://docs.litestar.dev/)
- **HTMX**: [htmx.org](https://htmx.org/)

### GitHub Repositories

- **python-oracledb**: [github.com/oracle/python-oracledb](https://github.com/oracle/python-oracledb)
- **Google ADK Python**: [github.com/google/adk-python](https://github.com/google/adk-python)
- **Litestar**: [github.com/litestar-org/litestar](https://github.com/litestar-org/litestar)

---

## Project Structure Reference

```
oracledb-vertexai-demo/
├── app/
│   ├── services/              # Business logic (SQLSpecService pattern)
│   │   ├── base.py            # SQLSpecService base class
│   │   ├── product.py         # Vector search, product queries
│   │   ├── vertex_ai.py       # Embedding generation, chat
│   │   ├── cache.py           # Two-level caching
│   │   └── adk/               # ADK agent system
│   │       ├── orchestrator.py  # Main coordinator
│   │       ├── agent.py         # LlmAgent definitions
│   │       ├── tools.py         # Tool wrappers (thin)
│   │       └── tool_service.py  # Tool business logic
│   ├── server/
│   │   ├── deps.py            # Dependency injection providers
│   │   └── controllers.py     # HTTP endpoints (Litestar)
│   ├── schemas/               # msgspec schemas for type safety
│   └── db/
│       └── migrations/        # SQL migrations with VECTOR types
├── docs/
│   └── guides/                # THIS DIRECTORY - comprehensive guides
└── .claude/
    ├── agents/                # AI agent definitions
    └── commands/              # Slash commands
```

---

## Contributing

We welcome improvements to these guides! When contributing:

1. **Maintain clarity**: Write for both humans and AI agents
2. **Include examples**: Real code from the project
3. **Test thoroughly**: Ensure all code examples work
4. **Cross-reference**: Link related topics appropriately
5. **Stay current**: Update "Last Updated" dates

Questions or suggestions? Open an issue or pull request.

---

**Happy coding! 🚀**
