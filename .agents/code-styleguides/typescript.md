# TypeScript Style Guide

Modern TypeScript with strict mode and functional patterns.

## Core Rules

### Strict Mode

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### Variable Declarations

```typescript
// Always use const by default
const items: Item[] = [];

// Use let only when reassignment is needed
let count = 0;
count++;

// Never use var
```

### Type Definitions

```typescript
// Use interface for object shapes
interface User {
  id: string;
  email: string;
  name?: string;  // Optional property
}

// Use type for unions, intersections, and aliases
type Status = 'pending' | 'active' | 'inactive';
type UserWithRole = User & { role: Role };

// Prefer T | null over T | undefined for explicit absence
function findUser(id: string): User | null {
  return users.get(id) ?? null;
}
```

### Avoid These

```typescript
// Never use any - prefer unknown
function bad(data: any) { ... }
function good(data: unknown) {
  if (typeof data === 'string') { ... }
}

// Never use {} - prefer Record or object
function bad(obj: {}) { ... }
function good(obj: Record<string, unknown>) { ... }

// Avoid type assertions when possible
const bad = data as User;  // Avoid
const good = parseUser(data);  // Validate instead

// Don't use non-null assertions without justification
const bad = user!.name;  // Avoid
const good = user?.name ?? 'Anonymous';  // Handle null
```

## Naming Conventions

| Concept          | Convention                     | Example                 |
| :--------------- | :----------------------------- | :---------------------- |
| Interfaces/Types | `PascalCase`                   | `UserProfile`           |
| Classes          | `PascalCase`                   | `UserService`           |
| Functions        | `camelCase`                    | `getUserById`           |
| Variables        | `camelCase`                    | `currentUser`           |
| Constants        | `SCREAMING_SNAKE_CASE`         | `MAX_RETRIES`           |
| Enums            | `PascalCase`                   | `UserStatus`            |
| Generics         | Single uppercase or `T` prefix | `T`, `TValue`, `TKey`   |

## Functions

```typescript
// Prefer function declarations for named functions
function calculateTotal(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Use arrow functions for callbacks and inline
const doubled = items.map((item) => item.value * 2);

// Explicit return types for public functions
export function parseConfig(raw: string): Config {
  return JSON.parse(raw);
}

// Optional parameters and defaults
function greet(name: string, greeting = 'Hello'): string {
  return `${greeting}, ${name}!`;
}
```

## Async/Await

```typescript
// Always use async/await over raw Promises
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch user: ${response.status}`);
  }
  return response.json();
}

// Handle cleanup with try/finally
async function withTransaction<T>(
  fn: (tx: Transaction) => Promise<T>
): Promise<T> {
  const tx = await beginTransaction();
  try {
    const result = await fn(tx);
    await tx.commit();
    return result;
  } catch (error) {
    await tx.rollback();
    throw error;
  }
}
```

## Error Handling

```typescript
// Create specific error classes
class NotFoundError extends Error {
  constructor(public readonly resource: string, public readonly id: string) {
    super(`${resource} not found: ${id}`);
    this.name = 'NotFoundError';
  }
}

// Use discriminated unions for result types
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

function parseJson<T>(raw: string): Result<T> {
  try {
    return { success: true, data: JSON.parse(raw) };
  } catch (error) {
    return { success: false, error: error as Error };
  }
}
```

## Module Organization

```typescript
// Named exports only - no default exports
export { UserService };
export type { User, UserCreate };

// Group imports
import { useState, useEffect, useCallback } from 'react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

import type { User } from './types';
import { UserService } from './service';
```

## Generics

```typescript
// Use descriptive generic names for complex types
interface Repository<TEntity, TId = string> {
  findById(id: TId): Promise<TEntity | null>;
  save(entity: TEntity): Promise<TEntity>;
  delete(id: TId): Promise<void>;
}

// Constrain generics appropriately
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

## Utility Types

```typescript
// Use built-in utility types
type UserInput = Omit<User, 'id' | 'createdAt'>;
type ReadonlyUser = Readonly<User>;
type PartialUpdate = Partial<User>;
type RequiredFields = Required<User>;

// Pick for selecting specific fields
type UserPreview = Pick<User, 'id' | 'name'>;
```

## Tooling

- **Formatter/Linter**: `prettier`/`eslint` OR `biome` (see `bun` skill)
- **Build**: `vite`, `esbuild`, or `tsc`
- **Test runner**: `vitest` or `bun test` (see `bun` skill)

## Performance Patterns

See `performance-patterns` skill for IPC and serialization details.

## Anti-Patterns

```typescript
// Bad: Using any
function process(data: any) { ... }

// Bad: Type assertions to silence errors
const user = response as User;

// Bad: Non-null assertions without reason
return items.find(i => i.id === id)!;

// Bad: Using namespace
namespace Utils { ... }

// Bad: Using default exports
export default function MyComponent() { ... }

// Bad: Ignoring Promise rejections
fetchData().catch(() => {});  // Swallows error

// Good alternatives:
fetchData().catch(console.error);  // At minimum, log
await fetchData();  // Let it propagate
```
