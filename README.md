# ☕ Oracle + Vertex AI Coffee Demo

An intelligent coffee recommendation system showcasing Oracle 23AI vector search with Google Vertex AI integration.

## 🚀 Quick Start

```bash
# Install dependencies with uv
make install

# Setup environment
cp .env.example .env  # Edit with your API keys

# Start Oracle 23AI
make start-infra

# Initialize database
uv run app database upgrade
uv run app database load-fixtures
uv run app database load-vectors

# Start the application
uv run app run
```

Visit [http://localhost:5006](http://localhost:5006) to try the demo!

## 📚 Documentation

For complete implementation and development guides, see the [`todo/`](todo/) directory:

- **[Quick Start Guide](todo/01-QUICK-START.md)** - Get running in 15 minutes
- **[Implementation Guide](todo/03-IMPLEMENTATION-PHASES-AA.md)** - Advanced Alchemy patterns
- **[Oracle Architecture](todo/ORACLE-ARCHITECTURE.md)** - Oracle 23AI features
- **[Conference Prep](todo/05-CONFERENCE-PREP.md)** - Demo presentation guide

## 🏗️ Architecture

This demo uses:

- **Oracle 23AI** - Complete data platform with native vector search
- **Vertex AI** - Google's generative AI platform for embeddings and chat
- **Advanced Alchemy** - Modern SQLAlchemy 2.0 patterns with repository pattern
- **Litestar** - High-performance async Python framework
- **HTMX** - Real-time UI updates without JavaScript complexity

## 🎯 For K-Scope Conference

This implementation is designed for conference demonstration with:

- Real-time chat interface
- Live Oracle performance metrics
- Demo control panel with personas
- Fallback modes for reliability
- Mobile-responsive design

## 🔧 Development Commands

```bash
# Database operations
uv run app database upgrade      # Apply migrations
uv run app database load-fixtures # Load sample data
uv run app database load-vectors  # Generate embeddings
uv run app database drop-all     # Drop all tables

# Development
uv run app run                 # Start the application
uv run pytest                  # Run tests
make lint                      # Code quality checks

# CLI Chat Interface
uv run app recommend           # Interactive coffee chat in terminal
```

## 📖 Additional Resources

- [Original Blog Post](https://cloud.google.com/blog/topics/partners/ai-powered-coffee-nirvana-runs-on-oracle-database-on-google-cloud/) - Background story
- [Oracle 23AI Vector Guide](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/) - Vector search documentation
- [Litestar Documentation](https://docs.litestar.dev) - Framework documentation
- [Advanced Alchemy Guide](https://docs.advanced-alchemy.litestar.org/) - Repository patterns

---

**Ready to showcase the power of Oracle 23AI + Vertex AI at your next conference!** 🎯
