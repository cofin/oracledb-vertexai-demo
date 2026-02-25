# Project Patterns

> Consolidated learnings and patterns from all flows.

## Code Conventions
- **Imports:** Place all imports at the top of the file. Avoid nested imports except for `TYPE_CHECKING` blocks.
- **Error Messages:** Write in lowercase without trailing periods. Include context where possible.
- **Naming:** Prefer snake_case for modules/functions, PascalCase for classes. Avoid "workaround" suffixes like `_optimized` or `_fallback`.

## Architecture Patterns
- **SQLSpec Service:** Service classes should wrap the SQLSpec driver and handle session management via async generators.
- **Oracle Vector Search:** Use `:name` style for parameter binding. Use `array.array('f', embedding)` for Oracle `VECTOR` type compatibility.
- **ADK Agents:** Use `LlmAgent` for reasoning. Tools must have full type hints and docstrings with `Args` and `Returns` sections.

## Gotchas & Warnings
- **Dead Code:** Never leave dead code in a reference application.
- **Oracle 23ai:** Native binary format (OSON) is preferred for JSON storage.
- **Vertex AI:** Use `RETRIEVAL_QUERY` for search queries and `RETRIEVAL_DOCUMENT` for product descriptions when creating embeddings.
