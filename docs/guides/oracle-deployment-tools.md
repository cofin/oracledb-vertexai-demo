# Oracle Deployment Tools Guide

Comprehensive guide to using `tools/oracle_deploy.py` for Oracle database management across all deployment modes.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Deployment Modes](#deployment-modes)
- [Command Reference](#command-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Overview

The `oracle_deploy.py` tool provides a unified CLI for managing Oracle databases across three deployment modes:

- **LOCAL**: Container-based Oracle 23 Free (Docker/Podman)
- **REMOTE**: On-premises Oracle instances
- **AUTONOMOUS**: Oracle Autonomous Database with wallet authentication

### Key Features

✅ **Unified Interface** - One command for all Oracle operations
✅ **Auto-Detection** - Automatically detects Docker or Podman
✅ **Multi-Mode Support** - Works with local, remote, and autonomous databases
✅ **Health Checks** - Built-in system diagnostics
✅ **Rich Output** - Color-coded, formatted terminal output
✅ **Wallet Management** - Complete autonomous database wallet support
✅ **Connection Testing** - Test connectivity across all modes

## Quick Start

### Check System Status

```bash
uv run python tools/oracle_deploy.py status
```

### Start Local Database

```bash
uv run python tools/oracle_deploy.py database start
```

### Install SQLcl

```bash
uv run python tools/oracle_deploy.py sqlcl install
```

### Configure Autonomous Wallet

```bash
uv run python tools/oracle_deploy.py wallet configure
```

### Test Connection

```bash
uv run python tools/oracle_deploy.py connect test
```

## Deployment Modes

### LOCAL Mode (Container-Based)

For local development with Oracle 23 Free in containers.

**Requirements:**
- Docker or Podman installed
- At least 8GB of available RAM
- 50GB of available disk space

**Environment Variables:**
```bash
ORACLE23AI_PORT=1521                  # Port mapping
ORACLE_SYSTEM_PASSWORD=super-secret    # SYSTEM password
ORACLE_PASSWORD=super-secret          # App user password
ORACLE_USER=app                       # App username
```

**Commands:**
```bash
# Start database
uv run python tools/oracle_deploy.py database start

# Check status
uv run python tools/oracle_deploy.py database status

# View logs
uv run python tools/oracle_deploy.py database logs -f

# Stop database
uv run python tools/oracle_deploy.py database stop

# Remove (with volumes)
uv run python tools/oracle_deploy.py database remove --volumes
```

### REMOTE Mode (On-Premises)

For connecting to existing Oracle instances.

**Requirements:**
- Network access to Oracle host
- Valid database credentials
- Oracle client installed (optional, for SQLcl)

**Environment Variables:**
```bash
DATABASE_HOST=oracle.example.com       # Oracle host
DATABASE_PORT=1521                     # Oracle port
DATABASE_SERVICE_NAME=ORCL             # Service name
DATABASE_USER=myuser                   # Username
DATABASE_PASSWORD=mypassword           # Password
```

**Commands:**
```bash
# Test connection
uv run python tools/oracle_deploy.py connect test

# Show connection info
uv run python tools/oracle_deploy.py connect info

# Check health
uv run python tools/oracle_deploy.py status
```

### AUTONOMOUS Mode (Cloud Database)

For Oracle Autonomous Database with wallet authentication.

**Requirements:**
- Wallet file (Wallet_*.zip) from Oracle Cloud
- Wallet password
- Valid database credentials

**Environment Variables:**
```bash
DATABASE_URL=oracle+oracledb://user:pass@service_high
WALLET_PASSWORD=wallet-password
WALLET_LOCATION=/path/to/wallet       # Wallet directory
TNS_ADMIN=/path/to/wallet            # Alternative
```

**Commands:**
```bash
# Extract wallet
uv run python tools/oracle_deploy.py wallet extract path/to/Wallet_DB.zip

# Configure wallet (interactive)
uv run python tools/oracle_deploy.py wallet configure

# List available services
uv run python tools/oracle_deploy.py wallet list-services

# Validate wallet
uv run python tools/oracle_deploy.py wallet validate

# Test connection
uv run python tools/oracle_deploy.py connect test
```

## Command Reference

### Database Commands

Manage local Oracle container lifecycle.

#### `database start`

Start Oracle 23 Free container.

```bash
uv run python tools/oracle_deploy.py database start [OPTIONS]
```

**Options:**
- `--pull` - Pull latest image before starting
- `--recreate` - Remove and recreate container if exists

**Example:**
```bash
# Start with latest image
uv run python tools/oracle_deploy.py database start --pull

# Force recreate
uv run python tools/oracle_deploy.py database start --recreate
```

#### `database stop`

Stop running database container.

```bash
uv run python tools/oracle_deploy.py database stop
```

#### `database restart`

Restart database container.

```bash
uv run python tools/oracle_deploy.py database restart
```

#### `database remove`

Remove database container.

```bash
uv run python tools/oracle_deploy.py database remove [OPTIONS]
```

**Options:**
- `--volumes` - Also remove data volumes

**Example:**
```bash
# Remove container only
uv run python tools/oracle_deploy.py database remove

# Remove container and volumes
uv run python tools/oracle_deploy.py database remove --volumes
```

#### `database logs`

View database container logs.

```bash
uv run python tools/oracle_deploy.py database logs [OPTIONS]
```

**Options:**
- `-f, --follow` - Follow log output
- `--tail N` - Show last N lines (default: 100)

**Example:**
```bash
# Follow logs in real-time
uv run python tools/oracle_deploy.py database logs -f

# Show last 50 lines
uv run python tools/oracle_deploy.py database logs --tail=50
```

#### `database status`

Show database container status.

```bash
uv run python tools/oracle_deploy.py database status
```

### SQLcl Commands

Manage Oracle SQLcl installation.

#### `sqlcl install`

Install Oracle SQLcl.

```bash
uv run python tools/oracle_deploy.py sqlcl install
```

Downloads and installs SQLcl to `~/.local/bin/`. Creates symlinks for `sql` and `sqlcl` commands.

#### `sqlcl verify`

Verify SQLcl installation.

```bash
uv run python tools/oracle_deploy.py sqlcl verify
```

Shows installation status, version, and PATH configuration.

#### `sqlcl uninstall`

Remove SQLcl installation.

```bash
uv run python tools/oracle_deploy.py sqlcl uninstall
```

### Wallet Commands

Manage Autonomous Database wallets.

#### `wallet extract`

Extract wallet zip file.

```bash
uv run python tools/oracle_deploy.py wallet extract WALLET_ZIP [OPTIONS]
```

**Arguments:**
- `WALLET_ZIP` - Path to Wallet_*.zip file

**Options:**
- `--dest DIR` - Destination directory (default: same as zip)

**Example:**
```bash
uv run python tools/oracle_deploy.py wallet extract .envs/tns/Wallet_DB.zip
```

#### `wallet configure`

Interactive wallet configuration wizard.

```bash
uv run python tools/oracle_deploy.py wallet configure [OPTIONS]
```

**Options:**
- `--wallet PATH` - Wallet directory or zip file

**Process:**
1. Locates wallet (auto-detect or specified path)
2. Extracts if zip file
3. Validates wallet contents
4. Parses available services
5. Generates .env configuration
6. Optionally sets TNS_ADMIN

**Example:**
```bash
# Auto-detect wallet
uv run python tools/oracle_deploy.py wallet configure

# Specify wallet path
uv run python tools/oracle_deploy.py wallet configure --wallet /path/to/wallet
```

#### `wallet list-services`

List available database services.

```bash
uv run python tools/oracle_deploy.py wallet list-services [OPTIONS]
```

**Options:**
- `--wallet PATH` - Wallet directory (auto-detect if not specified)

Shows all services with priority levels (high, medium, low, tp, tpurgent).

**Example:**
```bash
uv run python tools/oracle_deploy.py wallet list-services
```

#### `wallet validate`

Validate wallet configuration.

```bash
uv run python tools/oracle_deploy.py wallet validate [OPTIONS]
```

**Options:**
- `--wallet PATH` - Wallet directory (auto-detect if not specified)

Checks for required files and valid tnsnames.ora.

### Connection Commands

Test database connectivity.

#### `connect test`

Test database connection.

```bash
uv run python tools/oracle_deploy.py connect test [OPTIONS]
```

**Options:**
- `--timeout N` - Connection timeout in seconds (default: 10)

Auto-detects deployment mode and tests appropriate connection type.

**Example:**
```bash
# Quick connection test
uv run python tools/oracle_deploy.py connect test

# With custom timeout
uv run python tools/oracle_deploy.py connect test --timeout=30
```

#### `connect info`

Show connection configuration.

```bash
uv run python tools/oracle_deploy.py connect info
```

Displays current connection mode and configuration without actually connecting.

### System Commands

System-wide health checks.

#### `status`

Check overall system health.

```bash
uv run python tools/oracle_deploy.py status [OPTIONS]
```

**Options:**
- `--verbose` - Show detailed diagnostics

Checks:
- Container runtime (for MANAGED mode)
- Database container (for MANAGED mode)
- SQLcl installation
- Wallet configuration (for EXTERNAL mode)
- Database connectivity

**Example:**
```bash
# Quick health check
uv run python tools/oracle_deploy.py status

# Detailed diagnostics
uv run python tools/oracle_deploy.py status --verbose
```

## Configuration

### Environment Variables

The tool reads configuration from environment variables and `.env` files.

#### Common Variables

```bash
# Database credentials
DATABASE_USER=myuser
DATABASE_PASSWORD=mypassword
DATABASE_SERVICE_NAME=FREEPDB1
```

#### Local Mode

```bash
ORACLE23AI_PORT=1521
ORACLE_SYSTEM_PASSWORD=super-secret
ORACLE_PASSWORD=super-secret
ORACLE_USER=app
```

#### Remote Mode

```bash
DATABASE_HOST=oracle.example.com
DATABASE_PORT=1521
DATABASE_SERVICE_NAME=ORCL
```

#### Autonomous Mode

```bash
DATABASE_URL=oracle+oracledb://user:password@service_high
WALLET_PASSWORD=wallet-password
WALLET_LOCATION=/path/to/wallet
TNS_ADMIN=/path/to/wallet
```

### Auto-Detection Logic

The tool automatically detects deployment mode based on environment variables:

1. If `DATABASE_URL` and `WALLET_PASSWORD` → **AUTONOMOUS**
2. If `DATABASE_HOST` → **REMOTE**
3. Otherwise → **LOCAL**

## Troubleshooting

### Common Issues

#### "No container runtime available"

**Cause:** Docker/Podman not installed or not running.

**Solution:**
```bash
# Check Docker status
docker --version

# Or check Podman
podman --version

# Install Docker (Ubuntu/Debian)
sudo apt install docker.io

# Install Podman (Fedora/RHEL)
sudo dnf install podman
```

#### "Container does not exist"

**Cause:** Database container hasn't been started.

**Solution:**
```bash
uv run python tools/oracle_deploy.py database start
```

#### "Wallet not found"

**Cause:** Wallet not in expected locations.

**Solution:**
```bash
# Place wallet in .envs/tns/ or set environment variable
export WALLET_LOCATION=/path/to/wallet
uv run python tools/oracle_deploy.py wallet validate
```

#### "Connection failed"

**Cause:** Database not accessible or incorrect credentials.

**Solution:**
```bash
# Check system health for specific diagnostics
uv run python tools/oracle_deploy.py status --verbose

# Verify credentials in .env file
cat .env | grep DATABASE
```

#### SQLcl not in PATH

**Cause:** SQLcl installed but shell can't find it.

**Solution:**
```bash
# Add to PATH (bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Add to PATH (zsh)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Debug Mode

For detailed debugging, use the `--verbose` flag with status command:

```bash
uv run python tools/oracle_deploy.py status --verbose
```

## Examples

### Complete LOCAL Setup

```bash
# 1. Check system
uv run python tools/oracle_deploy.py status

# 2. Start database
uv run python tools/oracle_deploy.py database start --pull

# 3. Wait for healthy status (shown in start output)
uv run python tools/oracle_deploy.py database status

# 4. Test connection
uv run python tools/oracle_deploy.py connect test

# 5. Install SQLcl (optional)
uv run python tools/oracle_deploy.py sqlcl install
```

### Complete AUTONOMOUS Setup

```bash
# 1. Place wallet in .envs/tns/
mkdir -p .envs/tns
mv ~/Downloads/Wallet_MYDB.zip .envs/tns/

# 2. Configure wallet
uv run python tools/oracle_deploy.py wallet configure

# 3. List available services
uv run python tools/oracle_deploy.py wallet list-services

# 4. Update .env with credentials
cat >> .env <<EOF
DATABASE_USER=admin
DATABASE_PASSWORD=MyPassword123!
DATABASE_SERVICE_NAME=mydb_high
EOF

# 5. Test connection
uv run python tools/oracle_deploy.py connect test

# 6. Verify overall health
uv run python tools/oracle_deploy.py status
```

### Development Workflow

```bash
# Morning: Start database
uv run python tools/oracle_deploy.py database start

# During day: Check status
uv run python tools/oracle_deploy.py database status

# View logs if issues
uv run python tools/oracle_deploy.py database logs -f

# Restart if needed
uv run python tools/oracle_deploy.py database restart

# Evening: Stop database
uv run python tools/oracle_deploy.py database stop
```

### CI/CD Integration

```bash
# GitHub Actions example
name: Database Tests
jobs:
  test:
    steps:
      - name: Start Oracle
        run: uv run python tools/oracle_deploy.py database start --pull

      - name: Wait for healthy
        run: |
          while ! uv run python tools/oracle_deploy.py connect test; do
            sleep 5
          done

      - name: Run tests
        run: uv run pytest

      - name: Cleanup
        run: uv run python tools/oracle_deploy.py database remove --volumes
```

## Advanced Topics

### Container Runtime Selection

The tool auto-detects Docker or Podman, preferring Docker when both are available. To use a specific runtime:

```bash
# Force Docker (if both installed)
# Currently auto-detected only
# Future: Add --runtime flag
```

### Custom Container Configuration

Override defaults via environment variables:

```bash
# Custom port
export ORACLE23AI_PORT=1522

# Custom passwords
export ORACLE_SYSTEM_PASSWORD=MySystemPass123!
export ORACLE_PASSWORD=MyUserPass123!

# Custom user
export ORACLE_USER=myapp

uv run python tools/oracle_deploy.py database start
```

### Multiple Environments

Use different .env files for different environments:

```bash
# Development
uv run python tools/oracle_deploy.py --env-file=.env.dev database start

# Testing (future enhancement)
# Currently use shell env switching
export $(cat .env.test | xargs)
uv run python tools/oracle_deploy.py database start
```

## Migration from docker-compose

See [MIGRATION_GUIDE.md](../../tools/MIGRATION_GUIDE.md) for detailed migration instructions from `docker-compose.yml` to `oracle_deploy.py`.

## Support

For issues or questions:

1. Run: `uv run python tools/oracle_deploy.py status --verbose`
2. Check the detailed diagnostics and suggestions
3. Review command help: `uv run python tools/oracle_deploy.py <command> --help`
4. Consult [MIGRATION_GUIDE.md](../../tools/MIGRATION_GUIDE.md)

## Further Reading

- [Oracle 23 Free Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/23/index.html)
- [Oracle Autonomous Database](https://docs.oracle.com/en/cloud/paas/autonomous-database/index.html)
- [SQLcl User Guide](https://docs.oracle.com/en/database/oracle/sql-developer-command-line/)
- [Docker Documentation](https://docs.docker.com/)
- [Podman Documentation](https://docs.podman.io/)
