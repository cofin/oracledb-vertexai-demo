# Oracle SQLcl Usage Guide

Complete guide to using Oracle SQLcl for database operations, including traditional command-line usage and AI-powered MCP (Model Context Protocol) server functionality.

## Table of Contents

- [Introduction](#introduction)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Connection Management](#connection-management)
- [Common SQL Operations](#common-sql-operations)
- [SQLcl-Specific Features](#sqlcl-specific-features)
- [MCP Server Mode](#mcp-server-mode)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Logging](#monitoring-and-logging)
- [Examples and Use Cases](#examples-and-use-cases)

---

## Introduction

Oracle SQLcl (SQL Command Line) is Oracle's modern command-line interface for working with Oracle Database. It provides:

- **Traditional CLI**: All SQL*Plus functionality plus modern enhancements
- **MCP Server Mode**: AI-powered natural language database interactions
- **Advanced Features**: Formatting, scripting, database management

**Versions:**

- SQLcl 25.2+ includes MCP server support
- Compatible with Oracle Database 11g and later

---

## Installation

### Using manage.py (Recommended)

```bash
# Install SQLcl with automatic configuration
python3 manage.py install sqlcl

# Verify installation
sql -version
```

### Manual Installation

Download from [Oracle Technology Network](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/):

```bash
# Extract to ~/.local/sqlcl
unzip sqlcl-latest.zip -d ~/.local/

# Add to PATH
export PATH="$HOME/.local/sqlcl/bin:$PATH"

# Verify
sql -version
```

### Prerequisites

- **Java 11 or higher** (required)
- **Oracle Database** connection credentials

---

## Basic Usage

### Starting SQLcl

```bash
# Interactive mode
sql /nolog

# Direct connection (note the // before hostname)
sql user/password@//hostname:port/service_name

# Using TNS entry
sql user/password@tns_alias

# With wallet (Autonomous DB)
sql user/password@service_name
```

### Exit SQLcl

```sql
SQL> exit
-- or
SQL> quit
```

---

## Connection Management

### Connect to Database

```sql
-- Basic connection (note the // before hostname)
SQL> CONNECT user/password@//hostname:port/service_name

-- Using TNS
SQL> CONNECT user/password@tns_alias

-- Autonomous Database (with wallet)
SQL> CONNECT user/password@service_name_high
```

### Save Connection

```sql
-- Save connection for easy reuse (note the // before hostname)
SQL> CONN -save my_connection user/password@//localhost/freepdb1

-- Save with password for MCP use (note the // before hostname)
SQL> CONN -save my_connection -savepwd user/password@//localhost/freepdb1

-- List saved connections
SQL> CONN -list

-- Use saved connection
SQL> CONN my_connection
```

### Test Connection

```sql
-- Show current connection
SQL> SHOW USER

-- Test database connectivity
SQL> SELECT 'Connected!' FROM DUAL;
```

---

## Common SQL Operations

### Query Data

```sql
-- Simple query
SQL> SELECT * FROM products WHERE price > 10;

-- Formatted output
SQL> SET PAGESIZE 50
SQL> SET LINESIZE 120
SQL> SELECT product_id, name, price, category FROM products;

-- Export to CSV
SQL> SET SQLFORMAT CSV
SQL> SELECT * FROM products;
SQL> SPOOL products.csv
SQL> SELECT * FROM products;
SQL> SPOOL OFF
```

### Insert Data

```sql
SQL> INSERT INTO products (product_id, name, price, category)
     VALUES (101, 'Ethiopian Blend', 15.99, 'Coffee');
SQL> COMMIT;
```

### Update Data

```sql
SQL> UPDATE products
     SET price = 14.99
     WHERE product_id = 101;
SQL> COMMIT;
```

### Delete Data

```sql
SQL> DELETE FROM products
     WHERE product_id = 101;
SQL> COMMIT;
```

### Create Tables

```sql
SQL> CREATE TABLE customers (
       customer_id NUMBER PRIMARY KEY,
       name VARCHAR2(100),
       email VARCHAR2(100),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );
```

---

## SQLcl-Specific Features

### Formatting Output

```sql
-- Set output format
SQL> SET SQLFORMAT ANSICONSOLE  -- Pretty terminal output
SQL> SET SQLFORMAT JSON         -- JSON format
SQL> SET SQLFORMAT CSV          -- Comma-separated values
SQL> SET SQLFORMAT HTML         -- HTML table
SQL> SET SQLFORMAT XML          -- XML format
SQL> SET SQLFORMAT DEFAULT      -- Standard format

-- Example JSON output
SQL> SET SQLFORMAT JSON
SQL> SELECT * FROM products WHERE ROWNUM <= 3;
```

### DDL Operations

```sql
-- Generate DDL for a table
SQL> DDL products

-- Generate DDL for all tables
SQL> DDL

-- Save DDL to file
SQL> DDL products products_ddl.sql
```

### Information Commands

```sql
-- Describe table structure
SQL> DESC products

-- Show tables
SQL> TABLES

-- Show views
SQL> VIEWS

-- Show indexes
SQL> INDEXES

-- Database info
SQL> INFO
```

### Scripting

```sql
-- Run SQL script
SQL> @my_script.sql

-- Run with parameters
SQL> @my_script.sql param1 param2

-- List recent history
SQL> HISTORY

-- Re-run command from history
SQL> HISTORY 5
```

### Alias Commands

```sql
-- Create custom command alias
SQL> ALIAS myquery = SELECT * FROM products WHERE price > 10;

-- Use alias
SQL> myquery

-- List aliases
SQL> ALIAS
```

---

## MCP Server Mode

### What is MCP Mode?

MCP (Model Context Protocol) mode allows AI applications like Claude, ChatGPT, or Gemini CLI to interact with Oracle Database using natural language.

**Key Features:**

- Natural language to SQL translation
- AI-powered database operations
- Query generation and execution
- Schema exploration
- Report generation

### Starting MCP Server

```bash
# Start SQLcl in MCP server mode
sql -mcp
```

**Note:** MCP server is typically launched automatically by MCP client applications (Claude Desktop, Gemini CLI, etc.)

### MCP Client Configuration

#### Gemini CLI Configuration

Automatically configured by `manage.py`:

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

Location: `~/.gemini/settings.json`

#### Claude Desktop Configuration

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

Location:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### VS Code Cline Configuration

```json
{
  "mcpServers": {
    "sqlcl": {
      "command": "/path/to/bin/sql",
      "args": ["-mcp"],
      "disabled": false
    }
  }
}
```

### Setting Up MCP Connection

```sql
-- Save connection for MCP access (note the // before hostname)
SQL> CONN -save mcp_connection -savepwd user/password@//localhost/freepdb1

-- For Autonomous Database (uses TNS alias, no // needed)
SQL> CONN -save mcp_autonomous -savepwd admin/password@mydb_high
```

### Using MCP with Gemini CLI

Once configured, use natural language in Gemini CLI:

```bash
gemini

# Natural language queries:
> Show me all products
> What are the top 5 most expensive coffee products?
> Create a table for tracking customer orders
> Generate a sales report for last month
> Explain the schema of the products table
> Find all customers who ordered more than 3 times
```

### MCP Tools and Capabilities

SQLcl MCP server provides these tools to AI models:

1. **Query Execution** - Run SELECT statements
2. **DDL Operations** - CREATE, ALTER, DROP tables
3. **DML Operations** - INSERT, UPDATE, DELETE data
4. **Schema Exploration** - DESCRIBE tables, list objects
5. **Connection Management** - Switch connections
6. **Data Export** - Generate reports in various formats

---

### Best Practices for AI Agent Interaction with the `sqlcl` MCP Server

When using the `sqlcl` MCP server with an AI agent like Gemini, it's important to follow best practices to ensure efficient, safe, and predictable interactions. This section provides guidelines for developers on how to "teach" their agents to use the `sqlcl` MCP server effectively.

#### Agent Prompting Guide

The key to successful interaction with the `sqlcl` MCP server is to use clear, specific, and unambiguous prompts. Agents should be guided to ask for information in a way that minimizes the risk of data overload and avoids open-ended questions that can lead to loops.

**Good Prompts:**

*   "Show me a summary of the database schemas and the number of tables in each."
*   "List the first 10 products and the total number of products."
*   "Describe the schema of the 'products' table."
*   "What are the constraints on the 'orders' table?"
*   "Generate a sales report for the last 7 days, grouped by product category."

**Bad Prompts (to avoid):**

*   "Show me the database." (Too broad, could return a huge amount of data)
*   "Analyze the data." (Too vague, the agent might get into a loop of running different queries)
*   "Fix the database." (Too open-ended, could lead to unintended DDL/DML operations)

#### Tool Selection Guide

The `sqlcl` MCP server provides a variety of tools. Agents should be guided to use the most appropriate tool for the task at hand.

*   **For schema exploration:** Use the `DESCRIBE` command or ask for the schema of a specific table. This is much more efficient than running `SELECT *` and trying to infer the schema from the data.
*   **For data retrieval:** Be specific in your `SELECT` statements. Use `WHERE` clauses to filter the data and `LIMIT` (or `FETCH FIRST N ROWS ONLY` in Oracle) to limit the number of rows returned.
*   **For data modification (DML):** Always include a `WHERE` clause in your `UPDATE` and `DELETE` statements to avoid modifying more data than intended.
*   **For schema modification (DDL):** Be very careful with `CREATE`, `ALTER`, and `DROP` statements. These should ideally be reviewed by a human before execution.

#### Avoiding Common Pitfalls

*   **Loops:** Loops often occur when the agent is given a vague goal and tries to achieve it by repeatedly running the same or similar queries. To avoid this, provide the agent with clear, specific instructions and encourage it to ask clarifying questions if it's unsure how to proceed.
*   **Data Overload:** To avoid being overwhelmed with data, always ask for summarized or paginated results. For example, ask for the `COUNT(*)` of a table before asking for the data itself.

#### Caching Strategies

To improve performance and reduce the load on the database, consider implementing a caching strategy.

##### Application-Level Caching

You can implement a caching layer in your application that sits between the agent and the `sqlcl` MCP server. This can be done by creating a wrapper tool that caches the results of frequently executed queries.

**Example `cached_sql_query` Tool:**

```python
import functools
import time

# A simple in-memory cache with a timeout
def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_cache(func):
        @functools.lru_cache(maxsize=maxsize)
        def cached_func(args, kw, hashable_time):
            return func(args, kw)

        @functools.wraps(func)
        def wrapper_func(*args, **kwargs):
            return cached_func(args, frozenset(kwargs.items()), hashable_time=time.time() // seconds)

        return wrapper_func
    return wrapper_cache

@timed_lru_cache(seconds=300)
def cached_sql_query(sql: str) -> str:
    ''''''
    Executes a SQL query using the sqlcl MCP server and caches the result.
    ''''''
    # In a real implementation, this would call the sqlcl MCP server
    print(f"Executing query: {sql}")
    # result = call_sqlcl_mcp_server(sql)
    # return result
    return f"Result for query: {sql}"
```

##### Database-Level Caching (Oracle Result Cache)

Oracle provides a powerful feature called the **Oracle Result Cache** that can cache the results of queries at the database level. This is a very efficient way to speed up frequently executed queries.

To use the Oracle Result Cache, you can add the `/*+ RESULT_CACHE */` hint to your SQL queries.

**Example:**

```sql
SELECT /*+ RESULT_CACHE */ product_id, name, price
FROM products
WHERE category = 'Coffee';
```

The database will automatically cache the result of this query. The next time the same query is executed, the result will be fetched from the cache, which is much faster than re-executing the query.

**When to use Oracle Result Cache:**

*   For queries that are executed frequently.
*   For queries that access data that doesn't change often.
*   For queries that are complex and time-consuming to execute.

By combining smart prompting, appropriate tool selection, and caching, you can build powerful and efficient AI agents that can safely and effectively interact with your Oracle database through the `sqlcl` MCP server.

## Security Best Practices

### MCP Security Considerations

⚠️ **Critical Security Rules for MCP:**

1. **Never connect MCP to production databases**
   - Use development or test databases only
   - Use read-only replicas if possible

2. **Minimal Permissions**

   ```sql
   -- Create dedicated MCP user with limited permissions
   CREATE USER mcp_user IDENTIFIED BY secure_password;
   GRANT CONNECT TO mcp_user;
   GRANT SELECT ON products TO mcp_user;
   GRANT SELECT ON customers TO mcp_user;
   -- NO: GRANT DBA TO mcp_user;
   ```

3. **Monitor All Activity**
   - Check `DBTOOLS$MCP_LOG` regularly
   - Monitor sessions in `V$SESSION`
   - Review AI-generated queries

4. **User Confirmation**
   - Configure MCP client to prompt before executing
   - Review generated SQL before execution
   - Never run in fully external mode

### General SQLcl Security

```sql
-- Use secure connections
SQL> SET SECUREOPTION SSL

-- Don't save passwords in scripts
-- Use password prompts instead:
SQL> CONNECT user@database
Enter password: ********

-- Use wallets for Autonomous DB
-- Set TNS_ADMIN environment variable
export TNS_ADMIN=/path/to/wallet
```

---

## Monitoring and Logging

### MCP Logging Table

SQLcl MCP automatically creates `DBTOOLS$MCP_LOG` to track all interactions:

```sql
-- View MCP activity log
SQL> SELECT * FROM DBTOOLS$MCP_LOG
     ORDER BY logged_at DESC
     FETCH FIRST 10 ROWS ONLY;

-- Check queries from last hour
SQL> SELECT prompt, query_executed, logged_at
     FROM DBTOOLS$MCP_LOG
     WHERE logged_at > SYSTIMESTAMP - INTERVAL '1' HOUR;

-- Find specific AI requests
SQL> SELECT *
     FROM DBTOOLS$MCP_LOG
     WHERE prompt LIKE '%sales report%';
```

### Session Monitoring

```sql
-- Find SQLcl MCP sessions
SQL> SELECT sid, serial#, username, program, status
     FROM V$SESSION
     WHERE program LIKE '%SQLcl-MCP%';

-- Monitor active queries
SQL> SELECT s.sid, s.username, q.sql_text
     FROM V$SESSION s
     JOIN V$SQL q ON s.sql_id = q.sql_id
     WHERE s.program LIKE '%SQLcl-MCP%';
```

### Query Markers

All MCP-generated queries include a comment marker:

```sql
-- Example MCP query with marker
/* SQLcl-MCP: Generated query */
SELECT * FROM products WHERE category = 'Coffee';
```

---

## Examples and Use Cases

### Example 1: Basic Data Query

**Traditional SQLcl:**

```sql
SQL> CONNECT app/password@//localhost/freepdb1
SQL> SELECT product_id, name, price
     FROM products
     WHERE category = 'Coffee'
     ORDER BY price DESC;
```

**MCP Mode (via Gemini CLI):**

```
> Show me all coffee products sorted by price
```

### Example 2: Data Export

**Traditional SQLcl:**

```sql
SQL> SET SQLFORMAT CSV
SQL> SPOOL products_export.csv
SQL> SELECT * FROM products;
SQL> SPOOL OFF
```

**MCP Mode:**

```
> Export all products to CSV format
```

### Example 3: Schema Exploration

**Traditional SQLcl:**

```sql
SQL> DESC products
SQL> SELECT table_name FROM user_tables;
SQL> SELECT constraint_name, constraint_type
     FROM user_constraints
     WHERE table_name = 'PRODUCTS';
```

**MCP Mode:**

```
> Describe the products table
> Show me all tables in this database
> What are the constraints on the products table?
```

### Example 4: Creating Reports

**Traditional SQLcl:**

```sql
SQL> SET SQLFORMAT ANSICONSOLE
SQL> COLUMN category FORMAT A20
SQL> COLUMN total_sales FORMAT $999,999.99
SQL> SELECT category,
            COUNT(*) as product_count,
            AVG(price) as avg_price,
            SUM(price) as total_value
     FROM products
     GROUP BY category
     ORDER BY total_value DESC;
```

**MCP Mode:**

```
> Generate a summary report showing product count, average price,
  and total value by category
```

### Example 5: Complex Analysis

**Traditional SQLcl:**

```sql
SQL> WITH monthly_sales AS (
       SELECT TRUNC(order_date, 'MM') as month,
              SUM(total_amount) as sales
       FROM orders
       WHERE order_date >= ADD_MONTHS(SYSDATE, -6)
       GROUP BY TRUNC(order_date, 'MM')
     )
     SELECT TO_CHAR(month, 'YYYY-MM') as month,
            sales,
            LAG(sales) OVER (ORDER BY month) as prev_month,
            ROUND((sales - LAG(sales) OVER (ORDER BY month)) /
                  LAG(sales) OVER (ORDER BY month) * 100, 2)
              as growth_pct
     FROM monthly_sales
     ORDER BY month;
```

**MCP Mode:**

```
> Show me monthly sales for the last 6 months with
  month-over-month growth percentage
```

### Example 6: Database Maintenance

**Traditional SQLcl:**

```sql
-- Gather table statistics
SQL> EXEC DBMS_STATS.GATHER_TABLE_STATS('MYSCHEMA', 'PRODUCTS');

-- Check tablespace usage
SQL> SELECT tablespace_name,
            ROUND(bytes/1024/1024, 2) as size_mb,
            ROUND(maxbytes/1024/1024, 2) as max_mb
     FROM dba_data_files;
```

**MCP Mode:**

```
> Gather statistics for the products table
> Show me tablespace usage
```

---

## Advanced Features

### Liquibase Integration

SQLcl includes Liquibase for database change management:

```sql
-- Generate changelog
SQL> LB GENSCHEMA -split

-- Update database
SQL> LB UPDATE -changelog changelog.xml

-- Rollback changes
SQL> LB ROLLBACK-COUNT 1
```

### ORDS Integration

Deploy REST services directly from SQLcl:

```sql
-- Enable ORDS for schema
SQL> BEGIN
       ORDS.ENABLE_SCHEMA;
     END;
     /

-- Create REST service
SQL> BEGIN
       ORDS.DEFINE_SERVICE(
         p_module_name => 'products',
         p_base_path => '/products/',
         p_items_per_page => 25
       );
     END;
     /
```

### SQLcl JavaScript

Run JavaScript within SQLcl:

```sql
SQL> SCRIPT
var result = ctx.getConnection().createStatement()
  .executeQuery("SELECT COUNT(*) FROM products");
result.next();
print("Total products: " + result.getInt(1));
/
```

---

## Troubleshooting

### Common Issues

**Issue: "SQLcl requires Java 11 and above to run"**

```bash
# Check Java version
java -version

# Install Java (Ubuntu/Debian)
sudo apt install openjdk-17-jre-headless

# Install Java (RHEL/CentOS)
sudo dnf install java-17-openjdk
```

**Issue: "Connection refused"**

```sql
-- Check database listener
lsnrctl status

-- Verify connection details
SQL> CONNECT user/password@//localhost:1521/freepdb1
```

**Issue: "Wallet not found" (Autonomous DB)**

```bash
# Set wallet location
export TNS_ADMIN=/path/to/wallet

# Or specify in connection string
sql user/password@service_name?TNS_ADMIN=/path/to/wallet
```

**Issue: MCP Server Not Responding**

```bash
# Check if sql is in PATH
which sql

# Verify MCP mode starts
sql -mcp

# Check Gemini CLI configuration
cat ~/.gemini/settings.json
```

---

## Quick Reference

### Essential Commands

| Command | Purpose |
|---------|---------|
| `CONNECT` | Connect to database |
| `DESC` | Describe table structure |
| `TABLES` | List all tables |
| `DDL` | Generate DDL for objects |
| `INFO` | Show database info |
| `HISTORY` | Show command history |
| `SPOOL` | Save output to file |
| `SET SQLFORMAT` | Change output format |
| `ALIAS` | Create command shortcuts |

### Connection String Formats

```bash
# Standard format
user/password@host:port/service

# TNS alias
user/password@tns_name

# Easy Connect Plus
user/password@host/service?TNS_ADMIN=/wallet/path

# With SID
user/password@host:port:SID
```

### File Locations

- **SQLcl Installation**: `~/.local/sqlcl/`
- **Configuration**: `~/.sqlcl/`
- **Connection Save File**: `~/.sqlcl/connections.json`
- **Gemini MCP Config**: `~/.gemini/settings.json`
- **History**: `~/.sqlcl/history.txt`

---

## Integration with Project

### Local Development Setup

```bash
# 1. Install SQLcl
python3 manage.py install sqlcl

# 2. Start Oracle container
python3 manage.py database start

# 3. Connect via SQLcl
sql app/super-secret@//localhost:1521/freepdb1

# 4. Load fixtures (alternative to Python)
SQL> @db/migrations/001_initial_schema.sql
```

### Using with Gemini CLI

```bash
# 1. Install both tools
python3 manage.py install sqlcl
python3 manage.py install gemini-cli
# SQLcl MCP auto-configured!

# 2. Start Gemini with database access
gemini

# 3. Use natural language
> Connect to the local Oracle database
> Show me all products
> Create a sales report
```

---

## See Also

- [Oracle SQLcl Documentation](https://docs.oracle.com/en/database/oracle/sql-developer-command-line/)
- [Gemini MCP Integration Guide](gemini-mcp-integration.md)
- [Manage CLI Guide](manage-cli-guide.md)
- [Oracle Deployment Tools](oracle-deployment-tools.md)

---

## Appendix: Complete MCP Example

### Setup Process

```bash
# 1. Install prerequisites
python3 manage.py install sqlcl
python3 manage.py install gemini-cli

# 2. Save database connection for MCP (note the // before localhost)
sql /nolog
SQL> CONN -save local_dev -savepwd app/super-secret@//localhost/freepdb1
SQL> EXIT

# 3. Verify configuration
cat ~/.gemini/settings.json

# 4. Launch Gemini CLI
gemini
```

### Usage Session

```
Gemini CLI v2.5.0

> Connect to the local_dev database

✓ Connected to Oracle Database 23c Free

> Show me the products table schema

TABLE: PRODUCTS
- PRODUCT_ID (NUMBER) - Primary Key
- NAME (VARCHAR2(200)) - Not Null
- DESCRIPTION (CLOB)
- PRICE (NUMBER(10,2))
- CATEGORY (VARCHAR2(100))
- EMBEDDING (VECTOR)

> List all coffee products with prices over $12

| PRODUCT_ID | NAME                    | PRICE  |
|------------|-------------------------|--------|
| 5          | Ethiopian Yirgacheffe   | 18.99  |
| 12         | Colombian Supremo       | 15.49  |
| 23         | Jamaican Blue Mountain  | 24.99  |

3 rows returned

> Generate a monthly sales report

Generating report...
[Report data displayed]

> Thank you

Session ended. Database connection closed.
```

---

**Version**: 1.0
**Last Updated**: January 2025
**SQLcl Version**: 25.2+
