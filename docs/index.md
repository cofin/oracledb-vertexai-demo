# Ground Beans to Grounded Answers

```{rst-class} hero-tagline
Building Agentic Apps with Google and Oracle.
```

A working reference app that turns one chat message — *"I need something
bold"* — into a grounded answer. The user doesn't say "coffee"; the agent
reads the idiom, fires a vector search, and grounds the reply in real menu
rows.

::::{grid} 1 1 3 3
:gutter: 2
:class-container: hero-stack

:::{grid-item-card} {octicon}`search;1.2em` Vector search
:class-card: hero-pill

**Oracle 26ai** HNSW index over `VECTOR`.
:::

:::{grid-item-card} {octicon}`workflow;1.2em` Agentic flow
:class-card: hero-pill

**Google ADK 2.0** runs the agent and the intent classifier in parallel.
:::

:::{grid-item-card} {octicon}`zap;1.2em` Vertex AI
:class-card: hero-pill

`gemini-embedding-001` for retrieval, **Gemini** for the answer.
:::

::::

```{mermaid}
flowchart TD
    U([User question]) --> S{ADK Workflow start}
    S --> A[Coffee agent]
    S --> I[Intent classifier]
    A -- tool call --> O[(Oracle 26ai<br/>HNSW search)]
    O -- matches --> A
    A --> R[Grounded answer]
    I -.-> R
    R --> U
```

*Intent classification and the agent fan out from the same start node — the
agent decides when to fire a vector search, both branches join before the
answer streams back.*

## Where to go next

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Walkthrough
:link: tour
:link-type: doc

One chat message, end to end: question → embedding → Oracle → streamed
answer.
:::

:::{grid-item-card} Concepts
:link: concepts/vector-search
:link-type: doc

Vectors in Oracle, RAG, and how the Google ADK agent decides what to
retrieve.
:::

::::

```{toctree}
:hidden:
:caption: Concepts

tour
concepts/vector-search
concepts/rag
concepts/agent-flow
```

```{toctree}
:hidden:
:caption: Reference

reference/quickstart
reference/cli
reference/api
reference/internals
reference/developers
```
