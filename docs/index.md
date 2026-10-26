# Ground Beans to Grounded Answers

```{rst-class} hero-tagline
Building Agentic Apps with Google and Oracle.
```

A working reference app that turns one chat message — *"I need something
bold"* — into a grounded answer. The user never says "coffee"; the router
recognizes the idiom, runs an Oracle AI Database 26ai Hybrid Reciprocal Rank
Fusion search across `VECTOR(3072, FLOAT32)` embeddings and Oracle Text, and
grounds the reply in live menu, store, and inventory rows across both the
**Litestar 2** web app (`http://localhost:8000`) and the bundled **Oracle APEX
26.1** workspace (`https://localhost:8443/ords/apex`).

::::{grid} 1 1 2 4
:gutter: 2
:class-container: hero-stack

:::{grid-item-card} {octicon}`search;1.2em` Vector search
:class-card: hero-pill

**Oracle AI Database 26ai** HNSW `INMEMORY NEIGHBOR GRAPH` index over `VECTOR(3072, FLOAT32)`.
:::

:::{grid-item-card} {octicon}`workflow;1.2em` Hybrid RRF routing
:class-card: hero-pill

**Oracle 26ai Hybrid RRF** routes grounded product, store, availability, and order-status turns in one SQL round trip.
:::

:::{grid-item-card} {octicon}`zap;1.2em` Vertex AI
:class-card: hero-pill

`gemini-embedding-2` for `3072`-dim retrieval and **Gemini 3.8 Flash** for the native `AgentRuntime`.
:::

:::{grid-item-card} {octicon}`browser;1.2em` Oracle APEX 26.1
:class-card: hero-pill

Pre-bundled **APEX 26.1.5 + ORDS 26.3** calling Vertex AI (`COFFEE_VERTEX_AI`) via `APEX_AI.GENERATE`.
:::

::::

```{mermaid}
flowchart TD
    U([User question]) --> C[Litestar chat controller]
    C --> I{Hybrid RRF<br/>hybrid-search-turn}
    I -->|PRODUCT_RAG| P[Grounded product composer]
    I -->|STORE_LOCATION| S[Store lookup]
    I -->|PRODUCT_AVAILABILITY| V[Inventory lookup]
    I -->|ORDER_STATUS| D[Deterministic order-status notice]
    I -->|GENERAL_CONVERSATION| A[Native AgentRuntime]
    P --> O[(Oracle 26ai<br/>HNSW + Oracle Text)]
    S --> O
    V --> O
    A -. CallContext-bound tools .-> O
    O --> R[Grounded final event]
    D --> R
    A --> R
    R --> U
```

*Product, store, availability, and order-status turns are routed and handled
deterministically from a single Oracle AI Database 26ai Hybrid RRF round trip
(`hybrid-search-turn` + `hybrid-term-hits`) with SQLSpec `0.69.0` session
tracing and wire-level `sqlcommenter` tags. General conversation (and
low-confidence fallback) turns enter the native `AgentRuntime` (`google-genai`),
where **Gemini 3.8 Flash** invokes `CallContext`-bound Oracle tools.*

## Oracle APEX 26.1 + Vertex AI

`make start-infra` boots **Oracle Autonomous AI Database Free 26ai**
(`container-registry.oracle.com/database/adb-free:latest-26ai`, container
`cymbal-adb-free`), exports its mTLS wallet into `.envs/tns` (`myatp_low` on
TLS port `1522`), and serves pre-installed **Oracle APEX 26.1.5** and **ORDS
26.3** at `https://localhost:8443/ords/apex` (workspace `COFFEE`, parsing
schema `APP`, Database Actions at `https://localhost:8443/ords/sql-developer`).

The bundled APEXlang application in `src/apex/cymbal-coffee-ops/` (App ID
`100`, `compatibilityMode: 26.1`) connects `APEX_AI.GENERATE` (`p_service_static_id => 'COFFEE_VERTEX_AI'`) to **Gemini 3.8 Flash** on Vertex AI using either connectivity path:

1. **Method 1 (Primary): Direct Vertex AI OpenAI-Compatible Endpoint** — Oracle Database calls `https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi` directly over HTTPS (`DBMS_NETWORK_ACL_ADMIN` host ACEs for `aiplatform.googleapis.com:443`, `VERTEX_AI_CRED` Bearer credential, `COFFEE_VERTEX_AI` AI configuration with `model="google/gemini-3.8-flash"` and `Used by App Builder = Yes`), provisioned via `uv run python manage.py infra apex configure-vertex --mode direct --project "$VERTEX_AI_PROJECT_ID" --verify`.
2. **Method 2 (Secondary): Litestar OpenAI-Compatible Gateway** — Oracle Database calls `http://host.docker.internal:8000/api/apex/ai/v1` (`ApexAIController` in `src/app/domain/products/controllers/_apex_ai.py`) so Litestar authenticates to Vertex AI via Application Default Credentials with zero token expiry in APEX during local development (`uv run python manage.py infra apex configure-vertex --mode gateway --verify`).

## Where to go next

::::{grid} 1 1 2 3
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

:::{grid-item-card} {octicon}`browser;1.1em` Oracle APEX 26.1
:link: apex
:link-type: doc

Autonomous 26ai runtime, Direct Vertex AI vs Gateway, App 100 pages, and demo recordings.
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
:caption: Oracle APEX

apex
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
