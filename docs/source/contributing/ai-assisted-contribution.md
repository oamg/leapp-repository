# AI-assisted contribution guidance

This document provides upstream guidance for contributors who use AI coding
assistants (such as Cursor, Claude, Copilot, or similar tools). The guidance
complements the existing {doc}`Coding guidelines<coding-guidelines>` and
{doc}`PR guidelines<pr-guidelines>` - it does not replace them.

## AI files and skills

The AI-related files (harness) are located in the main repository directory:

- [`AGENTS.md`](https://github.com/oamg/leapp-repository/blob/main/AGENTS.md) —
  the main guidelines for agents. It describes the project architecture, repository layout,
  general contribution rules, common commands, and the Definition of Done (DoD) that every change must meet.
- [`CLAUDE.md`](https://github.com/oamg/leapp-repository/blob/main/CLAUDE.md) —
  imports `AGENTS.md` for Claude-oriented tools.
- [`skills/`](https://github.com/oamg/leapp-repository/tree/main/skills) —
  task-specific skill files (`SKILL.md`), each covering a particular contributor
  workflow:

  - **`leapp-actor-dev`** — Develop or modify actors. Covers actor structure,
    phase selection, placement rules and key constraints.
  - **`leapp-unit-tests`** — Write or fix unit tests. Covers test placement,
    mocking patterns and project conventions.
  - **`leapp-test-runner`** — Run tests and linters. Covers container-based CI
    testing, single-actor fast tests and lint commands.
  - **`leapp-code-review`** — Review code changes and PRs for upgrade safety,
    actor design, inhibitors, tests and project conventions.
  - **`leapp-commit-message-assist`** — Draft and improve commit titles/bodies
    and PR descriptions.

## How to use the AI skills

1. Point your AI tool at `AGENTS.md` so it loads the project context
   automatically (most tools detect it by convention).
2. When working on a specific task, open the matching skill file under
   `skills/<name>/SKILL.md`. The skill provides task-specific rules and
   checklists the tool can follow.
3. All standard contribution requirements still apply the AI skills reference
   the same coding guidelines, PR guidelines, and test expectations documented
   in this section.

## Expectations for AI-assisted contributions

```{important}
The human contributor is responsible for every change, regardless of how it was
produced.
```

In particular:
- Any commit with AI-generated content must carry an `Assisted-by: ...` clause.
- Follow the existing {doc}`Coding guidelines<coding-guidelines>` and
  {doc}`PR guidelines<pr-guidelines>`.
- Meet the DoD from `AGENTS.md`: scope is clear and limited,
  new or changed code is covered by unit tests, relevant checks were run
  (`make lint` and/or targeted tests), and risks or assumptions are called out.
- Review and understand all AI-generated code before submitting it.
