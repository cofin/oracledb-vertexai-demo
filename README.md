# ☕ Oracle + Vertex AI Coffee Demo

An intelligent coffee recommendation system showcasing Oracle 23AI vector search with Google Vertex AI integration.

## 🚀 Quick Start

### Recommended: Automated Setup (New!)

The fastest way to get started is using our unified management CLI:

```bash
# Install UV Python manager (if not already installed)
make install-uv
# Initialize project and install prerequisites
make install
uv run manage.py init --run-install

# Verify setup
uv run manage.py doctor

# Start Oracle 23ai (managed mode - local container)
uv run manage.py database oracle start-local-container

# Run database migrations
uv run app db upgrade

# Load sample data
uv run app db load-fixtures

# Start the application
uv run app run
```

Visit [http://localhost:5006](http://localhost:5006) to try the demo!

**Management CLI Commands:**

```bash
# Setup and initialization
uv run manage.py init                                          # Initialize project (creates .env interactively)
uv run manage.py install all                                   # Install all prerequisites
uv run manage.py doctor                                        # Verify setup and prerequisites

# Database management (managed mode - local container)
uv run manage.py database oracle start-local-container         # Start Oracle container
uv run manage.py database oracle stop-local-container          # Stop Oracle container
uv run manage.py database oracle restart-local-container       # Restart Oracle container
uv run manage.py database oracle local-container-logs          # View container logs
uv run manage.py database oracle wipe-local-container          # Remove container (clean slate)

# Database management (external mode - Autonomous DB)
uv run manage.py database oracle wallet extract Wallet_*.zip  # Extract wallet
uv run manage.py database oracle connect test                 # Test database connection

# Help
uv run manage.py --help                                        # Show all available commands
```

### Manual Setup

For more control over the setup process:

```bash
# Step 1: Install UV Python manager
make install-uv

# Step 2: Install project dependencies
make install

# Step 3: Initialize environment (creates .env interactively)
uv run manage.py init

# Step 4: Start Oracle 23AI container
make start-infra

# Step 5: Run database migrations
uv run app db upgrade

# Step 6: Load sample data
uv run app db load-fixtures

# Step 7: Start the application
uv run app run
```

**Reset Database (Clean Slate):**

To completely reset your local Oracle installation with no tables deployed:

```bash
make wipe-infra
# Then start fresh:
make start-infra
uv run app db upgrade
uv run app db load-fixtures
```

**Note:** Embeddings are included in the gzipped fixtures. To regenerate embeddings, use `uv run app coffee bulk-embed`.

## 🖼️ Screenshots

### Coffee Chat Interface

![Cymbal Coffee Chat Interface](docs/screenshots/cymbal_chat.png)

*AI-powered coffee recommendations with real-time performance metrics*

### Performance Dashboard

![Performance Dashboard](docs/screenshots/performance_dashboard.png)

*Live monitoring of Oracle vector search performance and system metrics*

## 📚 Documentation

### Choose Your Path

**🚀 I want to run the demo**
- [Quick Install (5 minutes)](#-quick-start) - Get started with automated setup
- [Demo Walkthrough](docs/guides/demo-walkthrough.md) - Step-by-step conference demo script *(coming soon)*

**🏗️ I want to deploy to production**
- [Cloud Deployment Guide](docs/guides/autonomous-database-setup.md) - Oracle Autonomous DB on GCP
- [Architecture Overview](docs/architecture/overview.md) - System design and components *(coming soon)*

**💻 I want to understand the code**
- [Architecture Overview](docs/architecture/overview.md) - High-level component interaction *(coming soon)*
- [Vector Search Deep Dive](docs/architecture/vector-search.md) - Oracle 23ai vector capabilities *(coming soon)*
- [AI Agent Architecture](docs/architecture/ai-agent.md) - Google ADK + Gemini integration *(coming soon)*

**🤝 I want to contribute**
- [Development Setup](CONTRIBUTING.md) - Contributing guidelines
- [SQLSpec Patterns](docs/guides/sqlspec-patterns.md) - Database patterns and best practices

### Current Documentation

#### Getting Started
- **Quick Start** - See [above](#-quick-start) for installation
- **[Autonomous Database Setup](docs/guides/autonomous-database-setup.md)** - Deploy to Oracle Autonomous DB on GCP
- **[Oracle Deployment Tools](docs/guides/oracle-deployment-tools.md)** - Unified `manage.py` CLI reference

#### Architecture & Technical Guides
- **[SQLSpec Migration](MIGRATION.md)** - Complete migration from litestar-oracledb to SQLSpec
- **[Oracle Vector Search](docs/guides/oracle-vector-search.md)** - Vector operations and HNSW indexes
- **[Litestar Framework](docs/guides/litestar-framework.md)** - Web framework patterns
- **[HTMX Integration](docs/htmx-migration-summary.md)** - HTMX integration details
- **[HTMX Events Reference](docs/htmx-events.md)** - Custom HTMX events

#### Additional Resources
- **[Architecture Updates](docs/architecture-updates.md)** - Recent improvements and migration history

## 🏗️ Architecture

This demo uses:

- **Oracle 23AI** - Complete data platform with native vector search
- **Vertex AI** - Google's generative AI platform for embeddings and chat
- **SQLSpec** - Modern database abstraction with Oracle-specific optimizations
- **Litestar** - High-performance async Python framework
- **HTMX** - Real-time UI updates without JavaScript complexity

### Database Layer

The application uses **SQLSpec** for type-safe, efficient database operations:

- ✅ **Automatic Vector Handling** - Native Oracle VECTOR type support
- ✅ **Connection Pooling** - Optimized async connection management
- ✅ **Type Safety** - Dict-based results with automatic mapping
- ✅ **Oracle Features** - Full support for MERGE, RETURNING, JSON operations
- ✅ **Flexible Deployment** - Managed container or external database (auto-detects wallet)

## 🎯 Key Features

This implementation is designed for conference demonstration with:

- **Real-time Chat Interface** - Personalized coffee recommendations with AI personas
- **Live Performance Metrics** - Oracle vector search timing and cache hit rates
- **In-Memory Caching** - High-performance response caching using Oracle
- **Native Vector Search** - Semantic similarity search without external dependencies
- **Intent Routing** - Natural language understanding via exemplar matching
- **Performance Dashboard** - Real-time monitoring of all system components

## 🔧 Development Commands

```bash
# Database operations (works with both managed and external modes)
uv run app db upgrade                # Run database migrations
uv run app db load-fixtures          # Load sample data
uv run app db export-fixtures        # Export database tables to JSON
uv run app coffee bulk-embed         # Generate embeddings for all products
uv run app coffee clear-cache        # Clear response cache
uv run app coffee model-info         # Show AI model configuration

# Development
uv run app run                       # Start the application
uv run pytest                        # Run tests
make lint                            # Code quality checks

# Infrastructure management (local containers)
make start-infra                     # Start Oracle 23ai container
make stop-infra                      # Stop Oracle 23ai container
make wipe-infra                      # Remove container (clean slate)
make infra-logs                      # Tail container logs

# For Autonomous Database deployments (external mode)
# See docs/guides/autonomous-database-setup.md for complete setup guide
```

## 📖 External Resources

- **[Original Blog Post](https://cloud.google.com/blog/topics/partners/ai-powered-coffee-nirvana-runs-on-oracle-database-on-google-cloud/)** - Origin story and motivation
- **[Oracle 23AI Vector Guide](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/)** - Official Oracle vector search documentation
- **[Litestar Documentation](https://docs.litestar.dev)** - Framework documentation
- **[Google Vertex AI](https://cloud.google.com/vertex-ai/docs)** - Vertex AI platform documentation
- **[SQLSpec](https://github.com/litestar-org/litestar-sqlspec)** - Database abstraction layer
