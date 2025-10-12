# ☕ Oracle + Vertex AI Coffee Demo

An intelligent coffee recommendation system showcasing Oracle 23AI vector search with Google Vertex AI integration.

## 🚀 Quick Start

### Recommended: Automated Setup (New!)

The fastest way to get started is using our unified management CLI:

```bash
# Initialize project and install prerequisites
uv run manage.py init --run-install

# Verify setup
uv run manage.py doctor

# Start Oracle 23ai (managed mode - local container)
uv run manage.py database oracle start

# Load sample data
uv run app load-fixtures

# Start the application
uv run app run
```

Visit [http://localhost:5006](http://localhost:5006) to try the demo!

**Management CLI Commands:**

```bash
python3 manage.py init                          # Initialize project (creates .env interactively)
python3 manage.py install all                   # Install all prerequisites
python3 manage.py doctor                        # Verify setup and prerequisites
python3 manage.py database oracle start         # Start Oracle container
python3 manage.py database oracle wallet extract Wallet_*.zip  # Extract wallet
python3 manage.py database oracle connect test  # Test database connection
python3 manage.py --help                        # Show all available commands
```

### Manual Setup

For more control over the setup process:

```bash
# Install UV Python manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
make install

# Setup environment (required - creates .env interactively)
python3 manage.py init

# Start Oracle 23AI
make start-infra
uv run app load-fixtures

# Start the application
uv run app run
```

**Note: Embeddings are included in the gzipped fixtures.**
If you'd like to regenerate embeddings, you can use:

```sh
uv run app db load-vectors
```

## 🖼️ Screenshots

### Coffee Chat Interface

![Cymbal Coffee Chat Interface](docs/screenshots/cymbal_chat.png)
_AI-powered coffee recommendations with real-time performance metrics_

### Performance Dashboard

![Performance Dashboard](docs/screenshots/performance_dashboard.png)
_Live monitoring of Oracle vector search performance and system metrics_

## 📚 Documentation

### Core Documentation

- **[Technical Overview](docs/system/01-technical-overview.md)** - High-level technical concepts
- **[Oracle Architecture](docs/system/02-oracle-architecture.md)** - Oracle 23AI unified platform
- **[Implementation Guide](docs/system/05-implementation-guide.md)** - Step-by-step build guide
- **[Demo Scenarios](docs/system/07-demo-scenarios.md)** - Live demonstration scripts

### Architecture & Migration

- **[SQLSpec Migration](MIGRATION.md)** - ✅ Complete migration from litestar-oracledb to SQLSpec
- **[SQLSpec Patterns](docs/guides/sqlspec-patterns.md)** - Database patterns and best practices
- **[Architecture Updates](docs/architecture-updates.md)** - Recent improvements:
  - ✅ **SQLSpec Migration** - Modern database abstraction layer
  - Native HTMX integration with Litestar
  - Centralized exception handling system
  - Unified cache information API
  - Enhanced cache hit tracking

### Technical Guides

- **[Oracle Deployment Tools](docs/guides/oracle-deployment-tools.md)** - Unified database management CLI
- **[Oracle Vector Search](docs/guides/oracle-vector-search.md)** - Vector operations guide
- **[Autonomous Database Setup](docs/guides/autonomous-database-setup.md)** - GCP deployment
- **[Litestar Framework](docs/guides/litestar-framework.md)** - Web framework patterns
- **[HTMX Events Reference](docs/htmx-events.md)** - Custom HTMX events
- **[HTMX Migration Summary](docs/htmx-migration-summary.md)** - HTMX integration details

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

See [MIGRATION.md](MIGRATION.md) for details on the SQLSpec architecture.

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
uv run app load-fixtures        # Load sample data
uv run app load-vectors         # Generate embeddings
uv run app truncate-tables      # Reset all data
uv run app clear-cache          # Clear response cache

# Autonomous Database specific
uv run app autonomous configure # Interactive setup wizard
# Export/Import (for faster demo startup)
uv run app dump-data           # Export all data with embeddings
uv run app dump-data --table intent_exemplar  # Export specific table
uv run app dump-data --path /tmp/backup --no-compress  # Custom options

# Development
uv run app run                 # Start the application
uv run pytest                  # Run tests
make lint                      # Code quality checks

# Makefile shortcuts
make config-autonomous         # Configure autonomous database
make install-autonomous        # Complete autonomous setup
make clean-autonomous-db       # Clean autonomous database
```

## 📖 Additional Resources

### Deployment Guides

- [Autonomous Database Setup](docs/guides/autonomous-database-setup.md) - Complete guide for Oracle Autonomous on GCP
- [Management CLI Guide](docs/guides/manage-cli-guide.md) - Complete guide for setup and deployment

### External Documentation

- [Original Blog Post](https://cloud.google.com/blog/topics/partners/ai-powered-coffee-nirvana-runs-on-oracle-database-on-google-cloud/) - Origin story
- [Oracle 23AI Vector Guide](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/) - Vector search documentation
- [Litestar Documentation](https://docs.litestar.dev) - Framework documentation
- [System Documentation](docs/system/) - Complete technical guides
