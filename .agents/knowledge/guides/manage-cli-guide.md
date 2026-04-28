# Manage CLI Guide

The `manage.py` CLI is a unified DevOps tool for managing Oracle + Vertex AI demo project setup, prerequisites, and database deployments.

## Quick Start

```bash
# Initialize project from scratch
python3 manage.py init --run-install --run-doctor

# Or step-by-step
python3 manage.py init              # Create .env, detect mode
python3 manage.py install all       # Install prerequisites
python3 manage.py doctor            # Verify setup
```

## Commands Overview

### Project Initialization

#### `init` - Initialize Project Environment

Sets up the project from scratch with interactive guidance.

```bash
python3 manage.py init [OPTIONS]

Options:
  --mode [managed|external]    Deployment mode (auto-detect if not specified)
  --run-install                Auto-run 'install all' after init
  --run-doctor                 Auto-run 'doctor' after init
  --non-interactive            Skip interactive prompts (use defaults)
```

**What it does:**

1. Detects or prompts for deployment mode (managed or external)
2. Creates `.env` file with interactive prompts for all settings
3. Configures database connection based on mode:
   - **Managed**: Standard container settings (localhost, known ports)
   - **External**: Choice of standard connection or wallet-based (Autonomous DB)
4. Auto-generates secure SECRET_KEY (64-character hex)
5. Configures Google Cloud / Vertex AI settings
6. Optionally installs prerequisites
7. Optionally verifies setup

**Deployment Modes:**

- **managed**: Deploy and manage Oracle container locally (Docker/Podman)
- **external**: Connect to existing database (on-prem, cloud, or Autonomous with wallet)

**Example:**

```bash
# Fully automated setup with managed mode
python3 manage.py init --run-install --run-doctor

# Interactive setup for external/autonomous database
python3 manage.py init --mode external

# Non-interactive with defaults (CI/automation)
python3 manage.py init --non-interactive --mode managed
```

**Note:** The `.env.example` file is no longer used. The `init` command creates `.env` from scratch with guided prompts.

---

### Installation Commands

#### `install all` - Install All Prerequisites

Installs all required and optional tools based on deployment mode.

```bash
python3 manage.py install all [OPTIONS]

Options:
  --mode [managed|external]          Install for specific mode
  --if-missing                       Only install if not present
  --yes, -y                          Skip confirmation prompts
```

**What it installs:**

- **All modes**: UV package manager
- **Managed mode**: Docker/Podman (verification only)
- **Optional**: Java, SQLcl, Gemini CLI, MCP Toolbox

#### `install list` - List Available Components

Shows all installable components with descriptions.

```bash
python3 manage.py install list
```

#### `install uv` - Install UV Package Manager

Installs Astral's UV Python package manager (required for all modes).

```bash
python3 manage.py install uv [OPTIONS]

Options:
  --version TEXT      Specific version (default: latest)
  --if-missing        Only install if not present
```

**Platforms supported:**

- Linux (x86_64, ARM)
- macOS (Intel, Apple Silicon)
- Windows (manual installation required)

#### `install sqlcl` - Install Oracle SQLcl

Installs Oracle's SQL command-line tool.

```bash
python3 manage.py install sqlcl [OPTIONS]

Options:
  --dir PATH    Installation directory (default: ~/.local/bin)
  --force       Reinstall even if already installed
```

**Prerequisites:**

- Java 11 or higher (auto-checked)

**Features:**

- Automatic Java validation
- Copy-paste installation commands for missing Java
- Auto-configures Gemini MCP integration if Gemini CLI is installed
- Executable permissions automatically set

**Gemini MCP Integration:**

When both SQLcl and Gemini CLI are installed, SQLcl is automatically configured as an MCP server in `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "sql",
      "args": ["-mcp"]
    }
  }
}
```

This allows you to use Oracle database operations directly in Gemini CLI!

#### `install gemini-cli` - Install Google Gemini CLI

Installs Google's AI-powered terminal assistant.

```bash
python3 manage.py install gemini-cli [OPTIONS]

Options:
  --if-missing    Only install if not present
```

**Prerequisites:**

- Node.js 18 or higher (auto-checked)

**Features:**

- Free tier: 60 requests/min, 1000 requests/day
- Access to Gemini 2.5 Pro
- 1M token context window
- Built-in tools: Google Search, file operations, shell commands

**Authentication:**

```bash
gemini  # Launch and login with Google account
```

#### `install mcp-toolbox` - Install MCP Toolbox for Databases

Installs Google's MCP Toolbox for database integration.

```bash
python3 manage.py install mcp-toolbox [OPTIONS]

Options:
  --if-missing       Only install if not present
  --version TEXT     Specific version (default: v0.16.0)
```

**Supported databases:**

- AlloyDB for PostgreSQL (including AlloyDB Omni)
- Cloud SQL (PostgreSQL, MySQL, SQL Server)
- Spanner
- Bigtable
- Self-managed MySQL and PostgreSQL

**Platform support:**

- Linux (amd64)
- macOS (Intel and Apple Silicon)
- Windows (amd64)

---

### Health & Verification

#### `doctor` - Verify Prerequisites

Comprehensive health check of all prerequisites and configuration.

```bash
python3 manage.py doctor [OPTIONS]

Options:
  --mode [local|remote|autonomous]   Check specific mode
  --json                             Output as JSON
  --verbose, -v                      Show detailed diagnostics
```

**What it checks:**

- `.env` file exists
- UV package manager installed
- Mode-specific requirements:
  - **Local**: Docker/Podman available
  - **Autonomous**: Wallet configuration valid
- Database connectivity (optional)

**Exit codes:**

- `0`: All checks passed
- `1`: One or more checks failed

**Example output:**

```
Health Check for 'local' Mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Checking .env file...
✓ .env file exists

📦 Checking UV package manager...
✓ UV installed: uv 0.8.15

🔧 Checking 'local' mode prerequisites...
✓ Docker found

✓ All checks passed!
```

---

### Database Operations

All database commands are now organized under the `database oracle` subcommand group.

#### `database oracle start` - Start Oracle Container

Starts Oracle 23 Free container (managed mode only).

```bash
python3 manage.py database oracle start [OPTIONS]

Options:
  --pull        Pull latest image before starting
  --recreate    Remove and recreate container if exists
```

#### `database oracle stop` - Stop Oracle Container

```bash
python3 manage.py database oracle stop [OPTIONS]

Options:
  --timeout INTEGER    Seconds to wait before forcing stop (default: 30)
```

#### `database oracle status` - Check Container Status

```bash
python3 manage.py database oracle status [OPTIONS]

Options:
  --verbose, -v    Show detailed status
```

---

### Wallet Management (External/Autonomous Mode)

Wallet commands are nested under `database oracle wallet`.

#### `database oracle wallet extract` - Extract Wallet Zip

Extracts Oracle Autonomous Database wallet.

```bash
python3 manage.py database oracle wallet extract WALLET_ZIP [OPTIONS]

Options:
  --dest PATH    Destination directory (default: .envs/tns)
```

**Example:**

```bash
python3 manage.py database oracle wallet extract ~/Downloads/Wallet_MyDB.zip
python3 manage.py database oracle wallet extract ~/Wallet_*.zip --dest ./my-wallet
```

#### `database oracle wallet configure` - Configure Wallet

Interactive wallet configuration wizard.

```bash
python3 manage.py database oracle wallet configure [OPTIONS]

Options:
  --wallet-dir PATH      Wallet directory
  --non-interactive      Skip interactive prompts
```

---

### Connection Testing

Connection commands are nested under `database oracle connect`.

#### `database oracle connect test` - Test Database Connection

Tests database connectivity for any deployment mode.

```bash
python3 manage.py database oracle connect test [OPTIONS]

Options:
  --mode [managed|external]   Mode to test (auto-detect if not specified)
  --timeout INTEGER           Connection timeout (default: 10s)
```

**Example:**

```bash
# Auto-detect mode from .env
python3 manage.py database oracle connect test

# Explicit mode
python3 manage.py database oracle connect test --mode external

# Custom timeout
python3 manage.py database oracle connect test --timeout 30
```

#### `status` - Overall System Health

Comprehensive health check of all components.

```bash
python3 manage.py status [OPTIONS]

Options:
  --verbose, -v                      Detailed diagnostics
  --mode [local|remote|autonomous]   Specific mode to check
```

---

## Deployment Modes

### Managed Mode

Uses Docker/Podman to run Oracle 23 Free container locally.

**Prerequisites:**

- UV package manager ✓
- Docker or Podman ✓

**Setup:**

```bash
python3 manage.py init --mode managed
python3 manage.py install all
python3 manage.py database oracle start
uv run app load-fixtures
```

**Configuration:** The init command will prompt for:

- DATABASE_USER (default: app)
- DATABASE_PASSWORD (default: super-secret)
- DATABASE_HOST (default: localhost)
- DATABASE_PORT (default: 1521)
- DATABASE_SERVICE_NAME (default: freepdb1)

### External Mode (Standard Connection)

Connects to existing on-prem or cloud Oracle instance using standard connection parameters.

**Prerequisites:**

- UV package manager ✓
- Network access to Oracle server ✓

**Setup:**

```bash
python3 manage.py init --mode external
# When prompted, select "no" for wallet-based connection
# Enter your database host, port, service name, credentials

python3 manage.py database oracle connect test
uv run app load-fixtures
```

**Configuration:** The init command will prompt for:

- DATABASE_USER
- DATABASE_PASSWORD
- DATABASE_HOST
- DATABASE_PORT
- DATABASE_SERVICE_NAME

### External Mode (Wallet-Based / Autonomous)

Uses Oracle Autonomous Database or any mTLS-secured connection with wallet.

**Prerequisites:**

- UV package manager ✓
- Oracle wallet files (Wallet\_\*.zip) ✓

**Setup:**

```bash
# 1. Initialize with wallet support
python3 manage.py init --mode external
# When prompted, select "yes" for wallet-based connection

# 2. Extract and configure wallet
python3 manage.py database oracle wallet extract ~/Downloads/Wallet_*.zip
python3 manage.py database oracle wallet configure

# 3. Test and load data
python3 manage.py database oracle connect test
uv run app load-fixtures
```

**Configuration:** The init command will prompt for:

- DATABASE_URL (format: `oracle+oracledb://USER:PASS@service_high`)
- WALLET_PASSWORD
- TNS_ADMIN (default: ./.envs/tns)

---

## Platform-Specific Instructions

### Java Installation

Required for SQLcl.

**Ubuntu/Debian:**

```bash
sudo apt update && sudo apt install -y default-jre
# Or specific version
sudo apt install openjdk-17-jre-headless
```

**RHEL/CentOS 7-8:**

```bash
sudo yum install java-17-openjdk
```

**RHEL/CentOS 9+, Fedora:**

```bash
sudo dnf install java-17-openjdk
```

**macOS:**

```bash
brew install openjdk@17
```

### Node.js Installation

Required for Gemini CLI.

**Ubuntu/Debian:**

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**RHEL/CentOS/Fedora:**

```bash
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs  # or dnf
```

**macOS:**

```bash
brew install node@20
```

---

## Troubleshooting

### UV not in PATH

After installing UV, you may need to add it to your PATH:

**Bash:**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### SQLcl requires Java

If you see "SQLcl requires Java 11 and above to run":

1. Check Java installation: `java -version`
2. If missing, install Java using platform-specific commands above
3. Reinstall SQLcl: `python3 manage.py install sqlcl --force`

### Docker not found (Local Mode)

Install Docker:

- Linux: https://docs.docker.com/engine/install/
- macOS: https://docs.docker.com/desktop/mac/install/
- Windows: https://docs.docker.com/desktop/windows/install/

Or use Podman as an alternative:

```bash
# Fedora/RHEL
sudo dnf install podman

# Ubuntu
sudo apt install podman
```

---

## Examples

### Complete Setup from Scratch

```bash
# 1. Initialize project (creates .env interactively)
python3 manage.py init --run-install --run-doctor

# 2. Start Oracle (managed mode)
python3 manage.py database oracle start

# 3. Load data
uv run app load-fixtures

# 4. Start application
uv run app run
```

### Install All Optional Tools

```bash
python3 manage.py install uv
python3 manage.py install sqlcl
python3 manage.py install gemini-cli
python3 manage.py install mcp-toolbox
python3 manage.py doctor --verbose
```

### Autonomous Database Setup

```bash
# 1. Initialize for external mode with wallet
python3 manage.py init --mode external
# When prompted, select "yes" for wallet-based connection

# 2. Extract and configure wallet
python3 manage.py database oracle wallet extract ~/Downloads/Wallet_MyDB.zip
python3 manage.py database oracle wallet configure

# 3. Test connection
python3 manage.py database oracle connect test

# 4. Load data and run
uv run app load-fixtures
uv run app run
```

---

## Integration with Gemini CLI

When both SQLcl and Gemini CLI are installed, SQLcl is automatically available as an MCP server in Gemini CLI.

**Usage in Gemini CLI:**

```bash
gemini  # Start Gemini CLI

# Inside Gemini CLI, you can now:
# - Query Oracle databases
# - Execute SQL commands
# - Get database schema information
# All through the MCP protocol!
```

---

## Tips

1. **Run `doctor` frequently** - It's a quick way to verify everything is working
2. **Use `--if-missing` flags** - Prevents reinstalling existing tools
3. **Check `install list`** - See all available components and their status
4. **Mode auto-detection** - Most commands detect your mode from `.env`
5. **Gemini + SQLcl** - Powerful combination for AI-assisted database work

---

## See Also

- [README.md](../../README.md) - Project overview and quick start
- [SQLcl Usage Guide](sqlcl-usage-guide.md) - Complete SQLcl reference with MCP examples
- [Gemini MCP Integration](gemini-mcp-integration.md) - AI-powered database interactions
- [Oracle Deployment Tools](oracle-deployment-tools.md) - Low-level tool documentation
