## Executive Summary
- The goal is to build a "SQL Lab" panel for the frontend React application.
- It needs to be simple, easy to use, themeable, and support SQL syntax highlighting.
- Several strong React components exist for this: `@monaco-editor/react`, `@uiw/react-textarea-code-editor`, and `react-simple-code-editor`.
- `react-simple-code-editor` combined with PrismJS or similar for SQL highlighting provides a very lightweight approach if full Monaco is too heavy.
- However, `@uiw/react-textarea-code-editor` is an extremely lightweight and simple code editor that already handles syntax highlighting natively.

## Codebase Analysis

### Relevant Modules
- `src/js/src/routes/` - New route needed for the SQL Lab.
- `src/js/src/components/` - Editor component will live here.
- `src/py/app/server/` - Backend API to actually execute the SQL against Oracle.

### Existing Patterns
- The frontend is using TanStack Router for routing.
- Styling is done via Tailwind CSS, utilizing CSS variables for dynamic theming (light/dark mode).
- Components are functional and use React Hooks.

## Library Documentation

### `@uiw/react-textarea-code-editor`
**Relevant APIs:**
- `CodeEditor`: Main component. Accepts `value`, `language="sql"`, `onChange`, and standard textarea props.

**Best Practices:**
- Import styles `import "@uiw/react-textarea-code-editor/dist.css";`.
- Set the `data-color-mode` attribute for theming.

**Gotchas/Warnings:**
- It is a wrapper around a standard textarea. While it provides highlighting, it does not provide advanced IDE features like auto-completion out of the box.

### `@monaco-editor/react`
**Relevant APIs:**
- `Editor`: Main component. Accepts `defaultLanguage="sql"`, `theme`, `value`.

**Best Practices:**
- Provides a full-fledged IDE experience in the browser (VS Code's editor).

**Gotchas/Warnings:**
- Can be heavy. Might require additional configuration with Vite for web workers, although the `@monaco-editor/react` wrapper simplifies this significantly.

### `react-simple-code-editor`
**Relevant APIs:**
- `Editor`: Needs to be supplied with a `highlight` function.

**Gotchas/Warnings:**
- Requires bringing your own syntax highlighter (like PrismJS), adding slight setup complexity compared to the UIW option.

## Prior Art

### External Patterns
- Database admin panels (like PopSQL, Supabase SQL editor) typically use Monaco for a robust experience.
- For simple "query runner" demos, a highlighted textarea is often sufficient and faster to load.

### Recommended Approach
Based on the requirement for a "simple, easy to use query panel" that is "themable and fits with our existing app":
1.  **Frontend Editor:** Start with `@uiw/react-textarea-code-editor`. It is extremely lightweight, easy to theme via standard CSS/Tailwind, and provides enough visual feedback (syntax highlighting) for a simple lab. If more power is needed later, upgrade to `@monaco-editor/react`.
2.  **Frontend Route:** Create `src/js/src/routes/sql-lab.tsx`. Add it to the routing tree and the landing page tiles.
3.  **Backend API:** Create a new Litestar endpoint (e.g., `POST /api/sql-lab/execute`) that accepts a SQL string and returns the JSON results. **Crucially, this needs to be read-only or strictly sandboxed if it's hitting a live database.**

**Rationale:** The UIW editor perfectly balances the need for a simple text area with the desire for syntax highlighting, without the massive bundle size overhead of Monaco.

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SQL Injection / Destructive Queries | High | High | The backend endpoint MUST restrict execution. Ideally, the Oracle connection used for this lab should have read-only privileges. Alternatively, strictly parse the SQL to only allow `SELECT` statements (though regex parsing is error-prone, a read-only user is much safer). |
| Heavy Payload | Low | Med | Use lightweight UIW editor instead of Monaco to keep the bundle small. Limit the number of rows returned by the backend (e.g., append `FETCH FIRST 100 ROWS ONLY`). |

### Integration Risks
- The frontend needs a new endpoint from the Python backend. This requires cross-stack coordination.

### Recovery Strategy
**Rollback Plan:** Remove the route from TanStack router and the link from the landing page.
**Checkpoint Strategy:** Checkpoint after implementing the frontend editor (mocked), and again after linking the backend execution.
