---
name: leapp-actor-dev
description: Develop or modify leapp-repository actors. Covers actor structure, phase selection, placement rules, and key constraints.
---

# Developing Leapp Actors

## Actor structure

Every actor follows layout:

```
repos/system_upgrade/<leapp_repo_dir>/actors/<actor_name>/
├── actor.py              # Actor class (thin wrapper)
├── libraries/
│   └── <actor_name>.py   # Implementation logic
└── tests/
    └── test_<actor_name>.py
```

Keep `actor.py` minimal — delegate the real implementation to the library for testability:

```python
from leapp.actors import Actor
from leapp.libraries.actor import <actor_name>
from leapp.models import <ConsumedModel>, <ProducedModel>
from leapp.tags import <PhaseTag>, IPUWorkflowTag


class MyActor(Actor):
    """Brief description of what this actor does."""

    name = '<actor_name>'
    consumes = (<ConsumedModel>,)
    produces = (<ProducedModel>,)
    tags = (IPUWorkflowTag, <PhaseTag>)

    def process(self):
        <actor_name>.process()
```

## Phase selection

| Intent | Phase tag | Rules |
|--------|-----------|-------|
| Collect system facts | `FactsPhaseTag` | Produce messages only, no decisions |
| Check compatibility / inhibit | `ChecksPhaseTag` | Consume facts, no direct system interaction |
| Modify application config | `ApplicationsPhaseTag` | Only after RPM upgrade is complete |
| Modify third-party config | `ThirdPartyApplicationsPhaseTag` | Same as above, for non-Red Hat apps |

### Common multi-actor patterns

**Inhibiting an incompatible system** (2 actors):
1. Scanner in `FactsCollectionPhase` — produces a facts message.
2. Checker in `ChecksPhase` — consumes facts, creates report / inhibits.

**Modifying incompatible config** (3 actors):
1. Scanner in `FactsCollectionPhase` — collects info.
2. Checker in `ChecksPhase` — decides and reports planned change.
3. Modifier in `ApplicationsPhase` — performs the change.

## Placement rules

- Reusable across upgrade paths → `repos/system_upgrade/common/`
- Specific to one path → `repos/system_upgrade/el8toel9/` or `el9toel10/`
- Same rule applies to models and shared libraries.


## Before writing new code

- Search existing actors/models/libraries — reuse before creating.
- Check if a model already provides the message you need (search model class names in `repos/`).
- Discover `repos/system_upgrade/common/libraries/` for shared utilities.
- Prefer using stdlib functions over shell commands.
- If introduce envars, use LEAPP and LEAPP_DEVEL.
- Write unit-testable code (see `skills/leapp-unit-tests/`).


## Key constraints

- Avoid running code on a module level to avoid slow downs during this load phase
- Never use `subprocess` — use `leapp.libraries.stdlib.run()` instead.
- Never interact with the system during `ChecksPhase`.
- Do not introduce new dependencies, unless it's strongly justified.


## Python compatibility

| Repository | Required Python versions |
|------------|--------------------------|
| `common`   | 3.6, 3.9, 3.12 |
| `el8toel9` | 3.6, 3.9 |
| `el9toel10`| 3.9, 3.12 |

## Reference

- [How to write an Actor for Leapp Upgrade](https://leapp-repository.readthedocs.io/latest/tutorials/howto-first-actor-upgrade.html)
- [Phases of the Upgrade Workflow](https://leapp-repository.readthedocs.io/latest/upgrade-architecture-and-workflow/phases-overview.html)
- [Coding guidelines](https://leapp-repository.readthedocs.io/latest/contributing/coding-guidelines.html)
- [Best Practices for actor development](https://leapp.readthedocs.io/en/stable/best-practices.html)
