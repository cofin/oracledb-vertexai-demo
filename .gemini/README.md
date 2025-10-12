# Gemini Agent System

This directory contains the configuration for a multi-role Gemini agent that replicates the functionality of the Claude agent system.

## How it Works

The Gemini agent uses a "super-agent" persona defined in `persona.md`. This persona allows the agent to adopt different roles based on keywords in your prompts:

- **Planner Role:** Triggered by the keyword "plan".
- **Expert Role:** Triggered by the keywords "implement" or "expert".
- **Tester Role:** Triggered by the keyword "test".
- **Reviewer Role:** Triggered by the keyword "review".

The detailed instructions for each role are defined in the `workflows` directory.

## How to Use

To use the Gemini agent, simply include the desired role's keyword in your prompt. For example:

- `gemini: plan to add a new feature for product recommendations`
- `gemini: implement the new feature`
- `gemini: test the new feature`
- `gemini: review the new feature`

The agent will then adopt the corresponding role and follow the instructions in the appropriate workflow file.
