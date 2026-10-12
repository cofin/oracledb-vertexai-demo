# Ground Beans to Grounded Answers

```{rst-class} hero-tagline
Building Agentic Apps with Google and Oracle.
```

A working reference app that turns one chat message — *"I need something
bold"* — into a grounded answer. The user doesn't say "coffee"; the router
recognizes the idiom, runs a vector search, and grounds the reply in real
menu rows.

::::{grid} 1 1 3 3
:gutter: 2
:class-container: hero-stack

:::{grid-item-card} {octicon}`search;1.2em` Vector search
:class-card: hero-pill

**Oracle 26ai** HNSW index over `VECTOR`.
:::

:::{grid-item-card} {octicon}`workflow;1.2em` Hybrid RRF routing
:class-card: hero-pill

**Oracle 26ai Hybrid RRF** routes grounded product, store, and availability turns in one SQL query.
:::

:::{grid-item-card} {octicon}`zap;1.2em` Vertex AI
:class-card: hero-pill

`gemini-embedding-2` for retrieval; **Gemini 3.8 Flash** powers the native `AgentRuntime`.
:::

::::

```{mermaid}
flowchart TD
    U([User question]) --> C[Litestar chat controller]
    C --> I{Hybrid RRF<br/>hybrid-search-turn}
    I -->|PRODUCT_RAG| P[Grounded product composer]
    I -->|STORE_LOCATION| S[Store lookup]
    I -->|PRODUCT_AVAILABILITY| V[Inventory lookup]
    I -->|GENERAL_CONVERSATION| A[Native AgentRuntime]
    P --> O[(Oracle 26ai<br/>HNSW + Oracle Text)]
    S --> O
    V --> O
    A -. optional tool .-> O
    O --> R[Grounded final event]
    A --> R
    R --> U
```

*Product, store, and availability turns are routed and grounded in a single
Oracle 26ai Hybrid RRF round trip (`hybrid-search-turn` + `hybrid-term-hits`).
General conversation enters the native `AgentRuntime` (`google-genai`), where
the model can invoke the same closure-bound tools.*

## Where to go next

::::{grid} 1 1 2 4
:gutter: 3

:::{grid-item-card} {octicon}`workflow;1.1em` Walkthrough
:link: tour
:link-type: doc

One chat message, end to end: question → embedding → Oracle → streamed
answer.
:::

:::{grid-item-card} {octicon}`database;1.1em` Concepts
:link: concepts/vector-search
:link-type: doc

Vectors in Oracle, RAG, and how the chat router chooses grounded service
calls.
:::

:::{grid-item-card} {octicon}`mortar-board;1.1em` Hands-on lab
:link: lab
:link-type: doc

Choose your deployment path: single-VM GCE or production-shaped Cloud Run.
:::

:::{grid-item-card} {octicon}`terminal;1.1em` Antigravity MCP
:link: mcp-antigravity
:link-type: doc

Clean SQLcl and Google MCP Toolbox configuration for teaching Antigravity
workflows.
:::

::::

```{toctree}
:hidden:
:caption: Concepts

tour
concepts/vector-search
concepts/rag
concepts/agent-flow
maps
```

```{toctree}
:hidden:
:caption: MCP

mcp-antigravity
```

```{toctree}
:hidden:
:caption: Lab

lab
lab-gce
lab-cloud-run
```

```{toctree}
:hidden:
:caption: Reference

reference/quickstart
reference/cli
reference/api
reference/internals
reference/developers
reference/brand-assets
```
