# Gemini CLI + MCP Integration Guide

This guide explains how the `manage.py` CLI automatically configures Gemini CLI with MCP (Model Context Protocol) extensions.

## Overview

When you install Gemini CLI using `manage.py`, it automatically detects and configures popular MCP extensions:

1. **SQLcl** - Oracle database operations (if SQLcl is installed)
2. **Sequential Thinking** - Advanced reasoning capabilities
3. **Context7** - Documentation lookup for popular libraries

## Installation

### Install Gemini CLI with Auto-Configuration

```bash
python3 manage.py install gemini-cli
```

**What happens:**
1. Checks for Node.js (installs via npm if available)
2. Installs `@google/gemini-cli` globally
3. **Detects SQLcl** - If installed, prompts to configure
4. **Prompts for Sequential Thinking** - Advanced reasoning MCP
5. **Prompts for Context7** - Documentation lookup MCP
6. Writes configuration to `~/.gemini/settings.json`

### Example Installation Flow

```
📦 Installing Google Gemini CLI...

✓ Node.js found: v20.11.0

Installing via npm...
Running: npm install -g @google/gemini-cli

✓ Gemini CLI installed successfully!

━━━━━━━━━ MCP Extensions Configuration ━━━━━━━━━━

Gemini CLI supports MCP (Model Context Protocol) extensions.
These extensions enhance Gemini with additional capabilities.


SQLcl (Oracle Database)
Oracle database operations and SQL execution
Configure SQLcl MCP server? [Y/n]: y
✓ SQLcl configured

Sequential Thinking
Advanced reasoning with step-by-step problem solving
Configure Sequential Thinking? [Y/n]: y

Context7
Documentation lookup for popular libraries and frameworks
Configure Context7? [Y/n]: y

MCP Configuration Summary:
  ✓ sqlcl (Oracle Database)
  ✓ sequential-thinking
  ✓ context7

First run:
  gemini  # Launch interactive CLI

Authentication:
  • Login with Google (free tier)
  • Or use API key from Google AI Studio
```

## MCP Extensions

### 1. SQLcl (Oracle Database)

**Automatically detected** when `sql` command is in PATH.

**Capabilities:**
- Execute SQL queries against Oracle databases
- Get database schema information
- Manage database connections
- Leverage MCP protocol for database operations

**Automatic Configuration:**

The `manage.py` CLI automatically handles SQLcl MCP configuration, including:

1. **Gemini MCP Server Settings** - Adds SQLcl to `~/.gemini/settings.json`
2. **Saved Connection with Password** - Creates a saved SQLcl connection using credentials from `.env`

This happens automatically when you:
- Run `python manage.py install sqlcl` (if Gemini CLI is installed)
- Run `python manage.py install gemini-cli` (if SQLcl is installed)

**Requirements:**

SQLcl MCP requires a saved connection with password. The CLI automatically creates this using:

```bash
# Reads from .env:
DATABASE_USER=app
DATABASE_PASSWORD=super-secret
DATABASE_HOST=localhost
DATABASE_PORT=1521
DATABASE_SERVICE_NAME=freepdb1

# Creates SQLcl saved connection (note the // before host):
conn -save mcp_demo -savepwd app/super-secret@//localhost:1521/freepdb1
```

**Configuration Files:**

```json
# ~/.gemini/settings.json
{
  "mcpServers": {
    "sqlcl": {
      "command": "sql",
      "args": ["-mcp"]
    }
  }
}
```

**Usage in Gemini CLI:**
```bash
gemini

# Inside Gemini CLI:
> Connect to Oracle database and show tables
> Execute: SELECT * FROM products WHERE price > 10
> Explain the schema of the users table
```

### 2. Sequential Thinking

**NPM Package:** `@modelcontextprotocol/server-sequential-thinking`

**Capabilities:**
- Multi-step problem solving
- Chain-of-thought reasoning
- Complex analysis and planning
- Iterative refinement of solutions

**Configuration:**
```json
{
  "mcpServers": {
    "sequential-thinking": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

**Usage in Gemini CLI:**
```bash
# Gemini will automatically use sequential thinking for complex problems:
> Design a microservices architecture for an e-commerce platform
> Debug this complex async/await issue step by step
> Plan a database migration strategy with rollback scenarios
```

### 3. Context7

**NPM Package:** `@upstash/context7-mcp`

**Capabilities:**
- Fetch up-to-date documentation for popular libraries
- Code examples from official docs
- API reference lookups
- Framework-specific guidance

**Supported libraries:**
- React, Next.js, Vue, Svelte
- Express, FastAPI, Django
- PostgreSQL, MongoDB, Redis
- AWS, GCP, Azure services
- And many more...

**Configuration:**
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

**Usage in Gemini CLI:**
```bash
> Show me how to use React hooks
> What's the latest way to handle authentication in Next.js 14?
> PostgreSQL full-text search examples
> How do I configure CORS in FastAPI?
```

## Installation Scenarios

### Scenario 1: Install Gemini CLI First, SQLcl Later

```bash
# Install Gemini CLI
python3 manage.py install gemini-cli
# ✓ gemini-cli installed
# ✓ sequential-thinking configured
# ✓ context7 configured

# Later, install SQLcl
python3 manage.py install sqlcl
# ✓ SQLcl installed
# ✓ Configured SQLcl as Gemini MCP server  ← Automatic!
```

### Scenario 2: Install SQLcl First, Gemini CLI Later

```bash
# Install SQLcl
python3 manage.py install sqlcl
# ✓ SQLcl installed
# ⚠ Gemini CLI not found (skipping MCP config)

# Later, install Gemini CLI
python3 manage.py install gemini-cli
# ✓ gemini-cli installed
# Detected SQLcl - prompts to configure  ← Automatic detection!
# ✓ sqlcl configured
# ✓ sequential-thinking configured
# ✓ context7 configured
```

### Scenario 3: Install Everything Together

```bash
# Install all at once
python3 manage.py install all
python3 manage.py install sqlcl
python3 manage.py install gemini-cli

# Result: Fully configured Gemini CLI with all MCP extensions
```

## Manual Configuration

If you need to manually edit MCP configuration:

### Location

```bash
~/.gemini/settings.json
```

### Full Example

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "sql",
      "args": ["-mcp"]
    },
    "sequential-thinking": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  },
  "security": {
    "auth": {
      "selectedType": "oauth-personal"
    }
  }
}
```

## Verification

### Check Configuration

```bash
# View Gemini settings
cat ~/.gemini/settings.json

# Test Gemini CLI
gemini --version

# Launch Gemini CLI
gemini
```

### Test MCP Extensions

```bash
gemini

# Test SQLcl (if configured)
> Connect to my Oracle database
> Show all tables

# Test Sequential Thinking
> Design a complex system architecture

# Test Context7
> Show me React Server Components documentation
```

## Troubleshooting

### SQLcl MCP Not Working

**Issue:** SQLcl commands not recognized in Gemini CLI

**Solution:**
```bash
# Verify SQLcl is in PATH
which sql
sql -version

# Check if .env is configured
cat .env | grep DATABASE_

# Reinstall SQLcl (will auto-configure password and MCP if Gemini CLI installed)
python3 manage.py install sqlcl --force
```

### Password Configuration Issues

**Issue:** SQLcl MCP connection fails due to missing password

**Symptoms:**
- "Invalid username/password" errors
- "No saved connection found" errors
- MCP server can't connect to database

**Solution:**
```bash
# Ensure .env has required variables
cat .env | grep -E 'DATABASE_(USER|PASSWORD|HOST|PORT|SERVICE_NAME)'

# Required in .env:
# DATABASE_USER=app
# DATABASE_PASSWORD=super-secret
# DATABASE_HOST=localhost
# DATABASE_PORT=1521
# DATABASE_SERVICE_NAME=freepdb1

# Reinstall to reconfigure (auto-configures password)
python3 manage.py install sqlcl --force

# Verify saved connection works
sql mcp_demo
```

### Node.js Extensions Not Loading

**Issue:** sequential-thinking or context7 not available

**Solution:**
```bash
# Ensure Node.js is installed
node --version  # Should be 18+

# Test npx can access packages
npx -y @modelcontextprotocol/server-sequential-thinking --version

# Reinstall Gemini CLI
python3 manage.py install gemini-cli --if-missing
```

### Gemini CLI Not Detecting Extensions

**Issue:** MCP servers configured but not appearing in Gemini

**Solution:**
1. Restart Gemini CLI completely
2. Check settings file syntax: `cat ~/.gemini/settings.json | python3 -m json.tool`
3. Verify `mcpServers` is at root level
4. Re-authenticate if needed

## Advanced Usage

### Custom MCP Extensions

You can add your own MCP servers to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "/path/to/my/mcp/server",
      "args": ["--option", "value"]
    }
  }
}
```

### Disable Specific Extensions

To disable an extension, remove it from `settings.json` or set it to `null`:

```json
{
  "mcpServers": {
    "sqlcl": null  // Disabled
  }
}
```

## Use Cases

### Database Development

```bash
gemini

> Connect to Oracle and explain the schema
> Generate SQL to find all orders from last month
> Help me optimize this slow query: SELECT ...
```

### Documentation Lookup

```bash
> How do I use FastAPI dependency injection?
> Show me Next.js 14 server actions examples
> PostgreSQL window functions documentation
```

### Problem Solving

```bash
> Debug this race condition in my async code
> Design a caching strategy for this API
> Plan a migration from monolith to microservices
```

## Integration with Project

### Use in Development Workflow

```bash
# Start Oracle database
python3 manage.py database start

# Launch Gemini CLI with database access
gemini

# Inside Gemini:
> Connect to local Oracle database
> Show me the products table schema
> Generate test data for the users table
> Help me write a migration script
```

### CI/CD Integration

```bash
# Non-interactive installation
python3 manage.py install gemini-cli --if-missing
# Skips MCP prompts in CI/CD environments
```

## Benefits

✅ **Zero Manual Configuration** - Everything set up automatically
✅ **Smart Detection** - Finds installed tools and configures them
✅ **Interactive Prompts** - User controls what gets configured
✅ **Non-Destructive** - Preserves existing MCP configurations
✅ **Comprehensive** - Database + AI + Documentation in one CLI

## See Also

- [Manage CLI Guide](manage-cli-guide.md) - Complete CLI reference
- [Oracle Deployment Tools](oracle-deployment-tools.md) - SQLcl setup
- [Gemini CLI Documentation](https://github.com/google-gemini/gemini-cli)
- [Model Context Protocol](https://modelcontextprotocol.io/)

## Quick Reference

```bash
# Install Gemini CLI with MCP auto-configuration
python3 manage.py install gemini-cli

# Install SQLcl with Gemini MCP integration
python3 manage.py install sqlcl

# Verify configuration
cat ~/.gemini/settings.json

# Launch Gemini CLI
gemini

# Get help
python3 manage.py install --help
```
