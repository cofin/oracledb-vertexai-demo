# Migration Guide: Oracle Deployment Tool Consolidation

## Overview

The Oracle deployment tools have been consolidated into a single, unified CLI tool: `tools/oracle_deploy.py`

**What Changed:**

- ✅ Removed `docker-compose.yml` (functionality moved to Python)
- ✅ Removed `tools/install_sqlcl.py` (integrated into main CLI)
- ✅ Removed `app database configure` command (moved to `oracle_deploy.py wallet configure`)
- ✅ Added comprehensive health checking and status reporting
- ✅ Added support for 3 deployment modes: Local, Remote, Autonomous

**Benefits:**

- Single tool for all Oracle deployment tasks
- Works with both Docker and Podman
- No docker-compose dependency
- Better error messages and troubleshooting
- Comprehensive health checks
- Rich formatted CLI output

---

## Command Migration

### Database Container Management

**Old (docker-compose):**

```bash
docker-compose up -d        # Start database
docker-compose down         # Stop database
docker-compose logs -f      # View logs
docker-compose ps           # Check status
```

**New (oracle_deploy.py):**

```bash
uv run python tools/oracle_deploy.py database start
uv run python tools/oracle_deploy.py database stop
uv run python tools/oracle_deploy.py database logs -f
uv run python tools/oracle_deploy.py database status
```

**Additional Commands:**

```bash
# Restart container
uv run python tools/oracle_deploy.py database restart

# Remove container (with confirmation)
uv run python tools/oracle_deploy.py database remove

# Remove container and volumes
uv run python tools/oracle_deploy.py database remove --volumes

# View logs (last 50 lines)
uv run python tools/oracle_deploy.py database logs --tail 50
```

---

### SQLcl Installation

**Old (install_sqlcl.py):**

```bash
python tools/install_sqlcl.py
```

**New (oracle_deploy.py):**

```bash
# Install SQLcl
uv run python tools/oracle_deploy.py sqlcl install

# Verify installation
uv run python tools/oracle_deploy.py sqlcl verify

# Uninstall SQLcl
uv run python tools/oracle_deploy.py sqlcl uninstall
```

---

### Wallet Configuration (Autonomous Database)

**Old (app CLI):**

```bash
uv run app database configure
```

**New (oracle_deploy.py):**

```bash
# Interactive configuration wizard
uv run python tools/oracle_deploy.py wallet configure

# Extract wallet zip file
uv run python tools/oracle_deploy.py wallet extract .envs/tns/Wallet_DB.zip

# List available services
uv run python tools/oracle_deploy.py wallet list-services

# Validate wallet files
uv run python tools/oracle_deploy.py wallet validate
```

---

## New Features

### Connection Testing

Test database connectivity for any deployment mode:

```bash
# Auto-detect mode and test connection
uv run python tools/oracle_deploy.py connect test

# Test specific mode
uv run python tools/oracle_deploy.py connect test --mode local
uv run python tools/oracle_deploy.py connect test --mode autonomous

# Display connection information
uv run python tools/oracle_deploy.py connect info
```

### System Health Check

Comprehensive health check of all components:

```bash
# Quick health check
uv run python tools/oracle_deploy.py status

# Detailed health check with verbose output
uv run python tools/oracle_deploy.py status --verbose

# Check specific deployment mode
uv run python tools/oracle_deploy.py status --mode local
```

**Health Check Components:**

- Container Runtime (Docker/Podman)
- Database Container (for LOCAL mode)
- SQLcl Installation (optional)
- Wallet Configuration (for AUTONOMOUS mode)
- Database Connectivity

---

## Environment Variables

All environment variables remain the same:

**Local Container Mode:**

```bash
ORACLE23AI_PORT=1521
ORACLE_SYSTEM_PASSWORD=super-secret
ORACLE_PASSWORD=super-secret
ORACLE_USER=app
```

**Autonomous Database Mode:**

```bash
DATABASE_URL=oracle+oracledb://user:password@service_name
WALLET_PASSWORD=wallet-password
WALLET_LOCATION=/path/to/wallet
# or
TNS_ADMIN=/path/to/wallet
```

**Remote Database Mode:**

```bash
DATABASE_HOST=remote-host
DATABASE_PORT=1521
DATABASE_SERVICE_NAME=ORCL
DATABASE_USER=user
DATABASE_PASSWORD=password
```

---

## Deployment Modes

The new tool supports 3 deployment modes with auto-detection:

### 1. Local (Container)

Uses Docker or Podman to run Oracle 23 Free container locally.

**Detection:** Default mode if no remote/autonomous config found

**Commands:**

```bash
uv run python tools/oracle_deploy.py database start
uv run python tools/oracle_deploy.py status
```

### 2. Remote (On-Prem)

Connects to existing Oracle database on remote host.

**Detection:** `DATABASE_HOST` environment variable is set

**Configuration:**

```bash
export DATABASE_HOST=oracle.example.com
export DATABASE_PORT=1521
export DATABASE_SERVICE_NAME=ORCL
export DATABASE_USER=app
export DATABASE_PASSWORD=secret
```

### 3. Autonomous (Cloud)

Connects to Oracle Autonomous Database using wallet.

**Detection:** `DATABASE_URL` and `WALLET_PASSWORD` are set

**Configuration:**

```bash
uv run python tools/oracle_deploy.py wallet configure
# Follow interactive wizard
```

---

## Quick Start Examples

### Start Local Development Database

```bash
# Start Oracle container
uv run python tools/oracle_deploy.py database start

# Check status
uv run python tools/oracle_deploy.py status

# Test connection
uv run python tools/oracle_deploy.py connect test

# View logs
uv run python tools/oracle_deploy.py database logs -f
```

### Configure Autonomous Database

```bash
# Configure wallet (interactive)
uv run python tools/oracle_deploy.py wallet configure

# Or extract manually
uv run python tools/oracle_deploy.py wallet extract .envs/tns/Wallet_DB.zip

# List services
uv run python tools/oracle_deploy.py wallet list-services

# Test connection
uv run python tools/oracle_deploy.py connect test --mode autonomous
```

### Install SQLcl

```bash
# Install
uv run python tools/oracle_deploy.py sqlcl install

# Verify
uv run python tools/oracle_deploy.py sqlcl verify

# Use SQLcl
sql app/password@localhost:1521/FREEPDB1
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check system health
uv run python tools/oracle_deploy.py status --verbose

# Check Docker/Podman
docker ps -a
# or
podman ps -a

# Remove and recreate
uv run python tools/oracle_deploy.py database remove --force
uv run python tools/oracle_deploy.py database start --pull
```

### Connection Failures

```bash
# Test connection with diagnostics
uv run python tools/oracle_deploy.py connect test

# Check connection info
uv run python tools/oracle_deploy.py connect info

# Verify container is healthy
uv run python tools/oracle_deploy.py database status
```

### Wallet Issues

```bash
# Validate wallet
uv run python tools/oracle_deploy.py wallet validate

# List services
uv run python tools/oracle_deploy.py wallet list-services

# Reconfigure
uv run python tools/oracle_deploy.py wallet configure
```

---

## Getting Help

```bash
# Main help
uv run python tools/oracle_deploy.py --help

# Command group help
uv run python tools/oracle_deploy.py database --help
uv run python tools/oracle_deploy.py sqlcl --help
uv run python tools/oracle_deploy.py wallet --help
uv run python tools/oracle_deploy.py connect --help

# Specific command help
uv run python tools/oracle_deploy.py database start --help
```

---

## Breaking Changes

1. **docker-compose.yml removed**
   - All functionality moved to `oracle_deploy.py`
   - Use `database` commands instead

2. **install_sqlcl.py removed**
   - Use `oracle_deploy.py sqlcl install` instead

3. **app database configure removed**
   - Use `oracle_deploy.py wallet configure` instead

---

## Migration Checklist

- [ ] Update scripts using `docker-compose` to use `oracle_deploy.py database`
- [ ] Update scripts using `install_sqlcl.py` to use `oracle_deploy.py sqlcl`
- [ ] Update documentation referencing old commands
- [ ] Test deployment workflows with new tool
- [ ] Update CI/CD pipelines if applicable
- [ ] Remove any `docker-compose.yml` references

---

## Support

For issues or questions:

1. Run `uv run python tools/oracle_deploy.py status --verbose` for diagnostics
2. Check the troubleshooting section above
3. Review error messages and suggestions provided by the tool
4. Report issues with full error output and health check results
