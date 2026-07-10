# AGENTS.md

## Project objective

[Leapp-repository](https://github.com/oamg/leapp-repository) contains the actors, models, and libraries for RHEL in-place upgrades (IPU). It runs on top of the [Leapp framework](https://github.com/oamg/leapp), which provides the actor runtime, workflow execution, messaging, and core CLI behavior. It's important to notice, that framework-level mechanics belong to leapp, while upgrade-path logic belong to leapp-repository.

## Architecture

Leapp IPU content is actor-based and message-driven:
- Actors exchange typed messages (`consumes` / `produces`) through workflow phases.
- Messages only flow forward: a producer must run before its consumer. Within the same phase, the framework resolves ordering automatically.
- Prefer scanner/checker design: collect facts in one actor, evaluate in another.
- Keep actor `process()` thin; place implementation logic in actor libraries for testability.

### Phase workflow (always apply)
- `FactsCollectionPhase`: collect system facts and produce messages
- `ChecksPhase`: consume previously collected facts, report/inhibit compatibility issues
- If modification is required, do it in later phases (`ApplicationsPhase` or `ThirdPartyApplicationsPhase`).
- `FinalPhase`: to perform actions after the upgraded system is booted.

For full phase details if ambiguous :
- [Phases of the Upgrade Workflow](https://leapp-repository.readthedocs.io/latest/upgrade-architecture-and-workflow/phases-overview.html#phases-overview)

### Repository Layout

```
├── system_upgrade/
    ├── common/                      # common repository/content used and accessible for all system upgrades
    │   ├── actors/<name>/
    │   │   ├── actor.py             # Actor class definition
    │   │   ├── libraries/           # Actor-private logic
    │   │   └── tests/               # Actor tests (unit_test_*.py, test_*.py)
    │   ├── models/                  # Data models (consumed/produced by actors)
    │   ├── topics/                  # Message topics
    │   └── libraries/               # Shared libraries (importable via leapp.libraries.common)
    ├── el8toel9/                     # content specific only for  RHEL 8 -> 9 upgrades
    └── el9toel10/                    # content specific only for  RHEL 9 -> 10 upgrades
```


## General rules (always apply)

- Follow leapp specific guidelines: docs/source/contributing/coding-guidelines.md and project conventions first.
- Follow Python coding guidelines: https://leapp.readthedocs.io/en/stable/contributing.html
- Analyze and plan before introducing code.
- Ask, don't assume. Be verbose when user input is unclear or can be interpreted in many ways.
- Explain your decisions briefly; expand detail only when requested.
- If multiple approaches or solution exists, pick simpler one.
- Be ready to undo your changes.
- Before introducing new code, check if it's not already solved in codebase. Avoid code duplication.
- Try to write as simple code as possible. New code should easy to read and understand even for non-experienced developers.
- Don't change code, which is not directly involved in given task. Don't try to improve unrelated code.
- Don't perform git commit, git push, or create PRs without explicit user request.



## Common Commands

Quick reference (details in skills below):

```bash
make lint                                    # pylint + flake8 + isort
TEST_CONTAINER=el9 make test_container       # full CI-equivalent test
ACTOR=<name> make dev_test_no_lint           # single-actor fast test
```

## Skills

Load the relevant skill for the task at hand:

- **Run tests / lint** → `skills/leapp-test-runner/`
- **Write or fix unit tests** → `skills/leapp-unit-tests/`
- **Develop or modify actors** → `skills/leapp-actor-dev/`
- **Draft commit / PR text** → `skills/leapp-commit-pr-text/`
- **Review code / PRs** → `skills/leapp-code-review/`


## Definition of Done

- Scope is clear and limited to the requested change.
- New or changed code is covered by unit tests.
- Relevant checks were run (`make lint` and/or targeted tests) and results are reported.
- Risks, assumptions, and follow-up work are explicitly called out
