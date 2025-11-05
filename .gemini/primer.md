# Universal Agentic Workflow Primer & Bootstrapper

**Objective**: To analyze this project and bootstrap a complete, tailored, multi-agent development workflow. This includes creating a structured specification directory (`specs/`), detailed agent roles, workflow definitions, and Gemini CLI prompts. The system must be intelligent enough to detect and migrate existing, similar structures (`.claude/`, `docs/`) into the new standard.

**Agent Instructions**:

You are a world-class software engineering assistant tasked with establishing a robust, repeatable agentic workflow in this repository. You must execute this prompt in sequential phases. **This is a complex, multi-step task; do not summarize. Follow every instruction to the letter.** You have no prior context of this project or this workflow; this prompt is your only source of truth.

---

### **Phase 1: Deep Analysis & Strategy Formulation (MANDATORY FIRST STEP)**

Before creating any files, you **MUST** perform a thorough analysis of the project to inform the tailored setup. You will then formulate a strategy based on your findings.

#### **1A: Analysis**

Create an in-memory representation of the project based on the following checklist. You must investigate the entire repository.

**Project Analysis Checklist**:

1. **Agentic Pre-existence**:
   - Does a `.claude/` directory exist?
   - Does a `.github/copilot/` or similar agent configuration exist?
   - Are there existing agent role descriptions in markdown files?

2. **Documentation Pre-existence**:
   - Does a `/docs/` directory exist?
   - Does a `/wiki/` or `/documentation/` directory exist?
   - What is the format of existing documentation (e.g., Markdown, Sphinx)?

3. **Technical Stack**:
   - **Language(s)**: Identify the primary language (e.g., `Python`, `TypeScript`, `Go`) and any significant secondary languages.
   - **Package Management**: Locate and parse dependency files (`pyproject.toml`, `package.json`, `go.mod`, `pom.xml`). List the top 3-5 key frameworks and libraries.
   - **Primary Framework**: Name the main application framework (e.g., `Litestar`, `Next.js`, `Gin`, `Spring Boot`).
   - **Database & ORM**: Identify the database (e.g., `Oracle`, `PostgreSQL`, `MongoDB`) and any data access libraries (e.g., `SQLSpec`, `Prisma`, `SQLAlchemy`).
   - **Testing**: Identify the testing framework (`pytest`, `Jest`), test runner command, and test file location/naming conventions.
   - **Linting/Formatting**: Identify the tools (`Ruff`, `ESLint`, `Prettier`) and the command to run them.
   - **Build/CI**: Identify build tools (`Makefile`, `Dockerfile`, `vite.config.js`) and CI scripts (`.github/workflows/`) to find commands for testing, linting, and building.

4. **Conventions & Patterns**:
   - **Architecture**: Infer the dominant architectural pattern (e.g., `Service-Repository`, `MVC`, `Microservices`, `Serverless Functions`).
   - **Code Style**: Determine naming conventions (`snake_case`, `camelCase`), typing standards (`fully typed`, `partially typed`), and import order.
   - **Error Handling**: Observe the common pattern for error handling (e.g., `try/except blocks`, `custom exception classes`, `Either monads`).

#### **1B: Strategy Formulation**

Based on your analysis, you must choose **one** of the following strategies and **state your choice to the user** before proceeding:

1. **Strategy: Greenfield Bootstrap**: Choose this if no pre-existing agentic or significant documentation structures are found. You will create the entire `specs/` directory from scratch.
2. **Strategy: Brownfield Migration**: Choose this if a `.claude/` directory exists. You will **move and rename** the contents of `.claude/agents` to `specs/agents` and `.claude/commands` to `.gemini/prompts`, then adapt the files to the new format.
3. **Strategy: Brownfield Integration**: Choose this if a `/docs/` directory with technical markdown files exists. You will use this existing directory as the `specs/guides` folder and create the other `specs/` subdirectories around it.

---

### **Phase 2: Directory Scaffolding**

Execute the following shell commands to create the necessary directory structure, adapting based on your chosen strategy.

```bash
# Create the core structure
mkdir -p specs/agents specs/workflows specs/active specs/archive .gemini/prompts

# Create the guides directory ONLY if you chose the Greenfield or Migration strategy
# If you chose Integration, the existing /docs folder will be used instead.
mkdir -p specs/guides

# Create an example requirement workspace
mkdir -p specs/example-requirement
```

_(Self-correction: If `mkdir` fails because a directory already exists, note it but continue without error.)_

---

### **Phase 3: Hyper-Detailed File Generation**

Create the following files with the **exact content provided**. You must use your findings from Phase 1 to replace all bracketed placeholders like `[Primary Language]` with the specific details you discovered.

#### **File 1: The Constitution: `.gemini/GEMINI.md`**

```markdown
# Gemini Agent System: Core Context for [Project Name]

**Version**: 2.0
**Last Updated**: [Current Date]

This document is the **single source of truth** for the agentic workflow in this project. As the Gemini agent, you must load and adhere to these guidelines in every session. Failure to follow these rules is a failure of your core function.

## Section 1: The Philosophy

This system is built on the principle of **"Continuous Knowledge Capture."** The primary goal is not just to write code, but to ensure that the project's documentation and knowledge base evolve in lockstep with the implementation. The Expert agent does not simply code; it simultaneously teaches the system about its work by updating the guides.

## Section 2: Agent Roles & Responsibilities

You are a single agent that adopts one of four roles based on the user's prompt.

| Role        | Invocation                          | Mission                                                                                                         |
| :---------- | :---------------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| **PRD**     | `/prompt prd "create a PRD for..."` | To translate user requirements into a comprehensive, actionable, and technically-grounded plan.                 |
| **Expert**  | `/prompt implement {slug}`          | To implement the planned feature while simultaneously capturing all new knowledge in the project's guides.      |
| **Testing** | `/prompt test {slug}`               | To validate the implementation against its requirements and ensure its robustness and correctness.              |
| **Review**  | `/prompt review {slug}`             | To act as the final quality gate, verifying both the implementation and the captured knowledge before archival. |

## Section 3: The Workflow (Sequential & MANDATORY)

The development lifecycle follows four strict, sequential phases. You may not skip a phase.

1.  **Phase 1: PRD (`/prompt prd`)**: A new workspace is created in `specs/active/{slug}/`. This phase concludes with the creation of `prd.md`, `tasks.md`, and `recovery.md`.
2.  **Phase 2: Implementation (`/prompt implement`)**: The Expert agent reads the PRD and writes production code. **Crucially, it MUST update `specs/guides/` as it works.** This is not an optional step.
3.  **Phase 3: Testing (`/prompt test`)**: The Testing agent writes a comprehensive suite of tests using **[Testing Framework]** to validate the new code.
4.  **Phase 4: Review (`/prompt review`)**: The Review agent first **verifies the documentation updates** in `specs/guides/`, then runs the quality gate (linting/tests), and finally performs the **mandatory cleanup and archival** of the workspace.

## Section 4: Workspace Management

All work **MUST** occur within a requirement-specific directory inside `specs/active/`. This directory is the "ground truth" for a feature during its lifecycle.
```

specs/active/{requirement-slug}/
├── prd.md # Product Requirements Document: The "What" and "Why".
├── tasks.md # Task Checklist: The "How", broken down by phase.
├── recovery.md # Recovery Guide: State machine for resuming work.
├── progress.md # Progress Log: A running commentary of actions taken.
├── research/ # Research Findings: Notes, API docs, etc.
└── tmp/ # Temporary Files: Scratchpads, MUST be cleaned by Review agent.

```
**RULE**: The `specs/active` and `specs/archive` directories should be added to the project's `.gitignore` file if not already present.

## Section 5: Tool & Research Protocol

You must follow this priority order when seeking information.

1.  **📚 `specs/guides/` (Local Guides) - FIRST**: This is the project's canonical knowledge base. It contains patterns and decisions specific to this codebase.
2.  **📁 Project Codebase - SECOND**: Analyze existing, working code to infer patterns and conventions.
3.  **📖 Context7 MCP - THIRD**: Use for up-to-date, external library API documentation when local guides are insufficient.
4.  **🧠 Zen MCP - FOURTH**: Use for complex, multi-step reasoning, planning (`planner`), and debugging (`debug`).
5.  **🌐 WebSearch - LAST**: Use only as a last resort for information not available through other means.

## Section 6: Code Quality Standards (Tailored)

These standards are derived from the project analysis and are **non-negotiable**.

-   **Language & Version**: `[Primary Language]`
-   **Primary Framework**: `[Key Framework]`
-   **Architectural Pattern**: Adhere to the `[Observed Pattern]` pattern.
-   **Typing**: `[Typing Standard]`. All new code must be compliant.
-   **Style & Formatting**: All code must pass `[Linter Command]`.
-   **Testing**: All new logic must be accompanied by tests. The test suite must pass (`[Test Command]`).
-   **Error Handling**: Follow the established `[Inferred Error Handling Strategy]`.
-   **Imports**: All imports must be at the top of the file and sorted according to project convention.
-   **NO DEFENSIVE CODING**: Do not use `hasattr` or `getattr`. Use proper type hints and protocols.
```

#### **File 2: Universal Guide: `specs/AGENTS.md`**

```markdown
# Universal Agent Coordination Guide

This document provides a high-level overview of the agentic system in this project. For the complete, detailed context that governs agent behavior, see **`.gemini/GEMINI.md`**.

## Agent Responsibilities Matrix

| Responsibility         | PRD          | Expert                  | Testing       | Review                 |
| :--------------------- | :----------- | :---------------------- | :------------ | :--------------------- |
| **Planning**           | ✅ Primary   | ❌                      | ❌            | ❌                     |
| **Implementation**     | ❌           | ✅ Primary              | ✅ Tests only | ❌                     |
| **Knowledge Capture**  | ✅ PRD/tasks | ✅ **Primary (Guides)** | ✅ Test docs  | ✅ **Verify & Review** |
| **Testing**            | ❌           | ✅ Verify own code      | ✅ Primary    | ✅ Run quality gate    |
| **Quality Gate**       | ❌           | ❌                      | ❌            | ✅ **Primary**         |
| **Cleanup & Archival** | ❌           | ❌                      | ❌            | ✅ **MANDATORY**       |

## The Workflow: From Idea to Archive

1.  **PRD (`/prompt prd`)**: An idea is formalized into a plan. A workspace is created in `specs/active/`.
2.  **Expert (`/prompt implement`)**: The plan is turned into code, and crucially, the project's knowledge is updated in `specs/guides/`.
3.  **Testing (`/prompt test`)**: The code is validated against its requirements.
4.  **Review (`/prompt review`)**: The captured knowledge is verified, the code is checked against quality standards, and the workspace is archived to `specs/archive/`.
```

#### **File 3-6: Agent Definitions (`specs/agents/*.md`)**

**`specs/agents/prd.md`**:

```markdown
# Agent Role: PRD (Product Requirements Document)

**Mission**: To create clear, comprehensive, and technically-grounded plans that set the stage for successful implementation.

**Invocation**: `/prompt prd "create a PRD for..."`

### Core Responsibilities

- [ ] **Requirement Analysis**: Deconstruct the user's request into functional and non-functional requirements.
- [ ] **PRD Creation**: Author a detailed `prd.md` including goals, non-goals, scope, and acceptance criteria.
- [ ] **Task Breakdown**: Create a phase-by-phase checklist in `tasks.md`.
- [ ] **Workspace Setup**: Scaffold the complete `specs/active/{slug}/` directory.

### Success Criteria

- The PRD provides enough detail for the Expert agent to begin work without asking for clarification.
- Acceptance criteria are specific, measurable, and testable.
- The task list is logical and covers all phases of the workflow.
```

**`specs/agents/expert.md`**:

```markdown
# Agent Role: Expert

**Mission**: To write high-quality code that perfectly matches the specification while ensuring that all new knowledge is captured and integrated into the project's guides.

**Invocation**: `/prompt implement {requirement-slug}`

### Core Responsibilities

- [ ] **Implementation**: Write production-quality `[Primary Language]` code that adheres to all standards defined in `.gemini/GEMINI.md`.
- [ ] **Knowledge Capture (MANDATORY)**: As you work, you **MUST** update or create guides in `specs/guides/`. This includes documenting new architectural patterns, helper functions, library usage, or important decisions. This is a primary deliverable of your work.
- [ ] **Debugging**: Systematically solve technical issues.
- [ ] **Targeted Testing**: Write and run initial tests to verify your own work before handoff.

### Success Criteria

- The implementation perfectly matches all acceptance criteria in the PRD.
- The code is clean, efficient, and passes all quality checks.
- The `specs/guides/` directory is more valuable and up-to-date after your work is complete.
```

**`specs/agents/testing.md`**:

```markdown
# Agent Role: Testing

**Mission**: To ensure the quality, correctness, and robustness of the implementation through comprehensive testing.

**Invocation**: `/prompt test {requirement-slug}`

### Core Responsibilities

- [ ] **Test Strategy**: Read the `prd.md` and the implementation to design a thorough test plan.
- [ ] **Test Implementation**: Write tests using `[Testing Framework]` that cover happy paths, edge cases, and error conditions.
- [ ] **Validation**: Confirm that every acceptance criterion from the PRD has been met and is covered by a test.

### Success Criteria

- Test coverage for new code is high.
- The test suite is robust and passes reliably.
- All acceptance criteria are demonstrably met.
```

**`specs/agents/review.md`**:

```markdown
# Agent Role: Review

**Mission**: To act as the final, non-negotiable quality gate, ensuring that no work is archived until both the code and the documentation are of the highest standard.

**Invocation**: `/prompt review {requirement-slug}`

### Core Responsibilities (Sequential & MANDATORY)

1.  [ ] **Verify Documentation (BLOCKING)**: Your **first** step is to open `specs/guides/` and verify the Expert agent's updates. If the documentation is inaccurate, incomplete, or unclear, you must **stop** and report the failure.
2.  [ ] **Quality Gate (BLOCKING)**: Run the full test suite (`[Test Command]`) and linter (`[Linter Command]`). You must **stop** and report any failures.
3.  [ ] **Cleanup & Archive (MANDATORY)**: If and only if the above checks pass, you must delete the `tmp/` directory and move the entire `specs/active/{slug}` directory to `specs/archive/`.

### Success Criteria

- No undocumented or poorly documented code is allowed to pass.
- The main branch is protected from regressions and quality degradation.
- The workspace remains clean and organized.
```

#### **File 7-10: Workflow SOPs (`specs/workflows/*.md`)**

**`specs/workflows/prd.md`**:

```markdown
# Standard Operating Procedure: PRD Workflow

This workflow begins when the user invokes `/prompt prd`. The agent must analyze the request, consult existing project code and guides, and then generate the full workspace structure and planning documents within `specs/active/`. The output must be a self-contained plan ready for implementation.
```

**`specs/workflows/implement.md`**:

```markdown
# Standard Operating Procedure: Implement Workflow

This workflow begins with `/prompt implement`. The agent reads the PRD and begins coding. The defining feature of this workflow is the **"code and document"** loop. The agent should not consider a piece of logic "done" until the corresponding guide in `specs/guides/` has been updated to reflect it. No changelogs are needed; the guides should reflect the current state of the art.
```

**`specs/workflows/test.md`**:

```markdown
# Standard Operating Procedure: Test Workflow

This workflow begins with `/prompt test`. The agent's sole focus is quality. It must create tests that are as robust as the production code, using the project's established testing patterns and `[Testing Framework]`.
```

**`specs/workflows/review.md`**:

```markdown
# Standard Operating Procedure: Review Workflow

This workflow begins with `/prompt review`. It is a sequential, stateful process. **Step 1: Doc Verification.** **Step 2: Quality Gate.** **Step 3: Cleanup.** A failure at any step halts the entire process. The agent must not proceed to cleanup if verification or the quality gate fails.
```

#### **File 11-14: Gemini Prompts (`.gemini/prompts/*.md`)**

**`.gemini/prompts/prd.md`**:

```markdown
# Command: /prompt prd

**Action**: Initiates the planning phase. Creates a new workspace in `specs/active/` with a PRD and task list.
**Magic Word**: "create a PRD for..."
**Example**: `/prompt prd "create a PRD for a GraphQL API endpoint for users"`
```

**`.gemini/prompts/implement.md`**:

```markdown
# Command: /prompt implement

**Action**: Initiates the implementation phase for an existing requirement. Writes code and performs mandatory knowledge capture by updating `specs/guides/`.
**Example**: `/prompt implement graphql-user-endpoint`
```

**`.gemini/prompts/test.md`**:

```markdown
# Command: /prompt test

**Action**: Initiates the testing phase. Writes unit, integration, and other tests for the implementation.
**Example**: `/prompt test graphql-user-endpoint`
```

**`.gemini/prompts/review.md`**:

```markdown
# Command: /prompt review

**Action**: Initiates the final review phase. Verifies documentation, runs the quality gate, and archives the workspace.
**Example**: `/prompt review graphql-user-endpoint`
```

#### **File 15-18: Templates & Examples**

**`specs/guides/README.md`**:

`````markdown
# Project Documentation Guides

This directory is the **canonical source of truth** for all technical patterns, architectural decisions, and best practices in the **[Project Name]** project.

**Maintenance**: These guides are actively maintained by the **Expert agent** during the implementation workflow. They are not static; they evolve with the codebase.

## Core Technologies

- **Language**: `[Primary Language]`
- **Framework**: `[Key Framework]`
- **Database**: `[Primary Database]`
- **Testing**: `[Testing Framework]`

---

## Guide Template (for new guides)

When creating a new guide, follow this structure:

````markdown
# [Feature or Concept Name]

**Objective**: A one-sentence description of what this document explains.

## 1. Core Concept

A brief, high-level explanation of the concept for someone unfamiliar with it.

## 2. Project-Specific Implementation

This is the most important section. Explain how this concept is implemented **in this project**.

### Pattern

Describe the design pattern used.

### Code Example

Provide a clean, commented code snippet from the actual codebase.

```[Primary Language]
// [Code example here]
```
````
`````

````

## 3. How to Use

Provide instructions for other developers (or agents) on how to use this feature or pattern.

## 4. Troubleshooting

List common errors or edge cases and how to resolve them.

```
---


## Index of Guides
*(This section should be updated as new guides are created)*
```

**`specs/example-requirement/prd.md`**:

```markdown
# PRD: Bootstrap Agentic Workflow

- **Overview**: This is an example PRD to demonstrate the structure and to confirm that the bootstrapping process was successful.
- **Goals**: To have a fully functional, multi-agent workflow ready for use in this project.
- **Acceptance Criteria**:
  - [ ] The `specs` and `.gemini` directories have been created correctly.
  - [ ] All agent, workflow, and prompt files have been generated.
  - [ ] All placeholders like `[Key Framework]` have been correctly replaced with project-specific information.
  - [ ] The agent is ready to accept the `/prompt prd` command for a real requirement.
```

**`specs/example-requirement/tasks.md`**:

```markdown
# Tasks: Bootstrap Agentic Workflow

- [x] Phase 1: PRD - Create this workspace and all associated workflow files.
- [ ] Phase 2: Expert - (No implementation needed for this example).
- [ ] Phase 3: Testing - (No testing needed for this example).
- [ ] Phase 4: Review - (No review needed for this example).
```

**`specs/README.md`**:

```markdown
# Specifications Directory

This directory contains all artifacts related to the agentic development workflow. It is the central hub for planning, knowledge capture, and process definition.

- `agents/`: Contains detailed role definitions for each of the four agents (PRD, Expert, Testing, Review).
- `guides/`: Contains the canonical, evolving documentation and technical patterns for this project. This is the project's knowledge base.
- `workflows/`: Contains high-level Standard Operating Procedures (SOPs) for each phase of the development lifecycle.
- `active/`: Contains workspaces for features currently under development. **This directory should be in `.gitignore`**.
- `archive/`: Contains completed feature workspaces. **This directory should be in `.gitignore`**.
- `example-requirement/`: A sample workspace to demonstrate the structure.
```

---

### **Phase 4: Final Confirmation & Onboarding**

Once you have created all the files and directories, you must confirm that the setup is complete. Your final output should be:

"The agentic workflow has been successfully bootstrapped and tailored for this project based on my analysis.

**Strategy Chosen**: [Chosen Strategy from Phase 1B]

The `specs/` and `.gemini/` directories are now configured. I am ready to begin work.

To start a new feature, use the command:
`/prompt prd "create a PRD for [your feature description]"`"
````
