# SQLSpec Migrations

This directory contains database migration files.

## File Format

Migration files use SQLFileLoader's named query syntax with versioned names:

```sql
-- name: migrate-0001-up
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- name: migrate-0001-down
DROP TABLE example;
```

## Naming Conventions

### File Names

Format: `{version}_{description}.sql`

- Version: Zero-padded 4-digit number (0001, 0002, etc.)
- Description: Brief description using underscores
- Example: `0001_create_users_table.sql`

### Query Names

- Upgrade: `migrate-{version}-up`
- Downgrade: `migrate-{version}-down`

This naming ensures proper sorting and avoids conflicts when loading multiple files.
