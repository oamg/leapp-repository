---
name: leapp-code-review
description: >-
  Review leapp-repository code changes and pull requests for upgrade safety,
  actor design, inhibitors, tests, and project conventions. Use when reviewing
  a PR, a branch, a diff, or when the user asks for a code review.
---

# Code review (leapp-repository)

## Scope

Find problems in a change set. Sort by importance.

Do not repeat rules from other skills — cite the skill and explain why the diff breaks the rule. Related skills:
- Actor structure, phases, placement, Python versions: `skills/leapp-actor-dev/` + `AGENTS.md`
- Unit tests: `skills/leapp-unit-tests/`
- Running lint/tests: `skills/leapp-test-runner/`
- Commit/PR text: `skills/leapp-commit-message-assist/`

Load a linked skill only when a specific finding needs the full rule.

Do not push, merge, or create PRs unless the user asks.

## Workflow

1. Get the full change set: PR URL, `git diff <base>...HEAD`, or files the user points at. Use the full branch diff, not only the latest commit.
2. Read PR description and commit messages for intent. Flag missing context; point to `leapp-commit-message-assist` for rewording.
3. Check the diff against the checklist below.
4. Run unit tests for affected actors (`skills/leapp-test-runner/`) and verify they pass.
5. Report findings using the output format. Start with blockers.
6. When uncertain, state confidence: `[Certain]` / `[Likely]` / `[Speculative]`.

## Output format

```markdown
## Summary
<1-3 sentences: what the change does and whether it is ready>

## Findings

### Blockers (upgrade will fail or produce wrong result)
- **[area]** <problem> — <why it matters> — <how to fix> (cite skill if needed)

### Major (wrong pattern, weak tests, unclear reports)
- ...

### Minor (style, naming — skip if trivial)
- ...

### Questions
- ...
```

Prefer fewer important comments over many small style notes.

## Review checklist

### Upgrade safety (primary focus)

- [ ] Blocking conditions use inhibitors (`reporting.Groups.INHIBITOR`)
- [ ] Non-blocking issues are reported, not silently ignored
- [ ] Report text tells the operator what is wrong and how to fix it
- [ ] Edge cases handled: missing files, empty messages, partial configs, unexpected architectures or versions
- [ ] External command failures caught (`CalledProcessError`; `OSError` when the binary may be missing)
- [ ] Environment variables use `LEAPP_` prefix and `get_env`, not bare `os.environ` (bare env does not survive reboots)

### Actor design (cite `leapp-actor-dev` / `AGENTS.md`)

- [ ] Facts collection vs. decision/inhibit/modify are in the correct actors and phases
- [ ] Consumed/produced models match `api.consume` / `api.produce` usage; producer runs before consumer
- [ ] No new models or utilities that duplicate what already exists
- [ ] Change is limited to the stated problem; no unrelated edits

### Commit structure and granularity

- [ ] Each commit is one logical unit, independently revertable without breaking `main`
- [ ] Fewer well-structured commits preferred over many trivial ones
- [ ] Fixups are squashed before review (suggest `git commit --fixup` + autosquash rebase if not)
- [ ] Total commit count reasonable (under ~15)
- [ ] Multi-actor features grouped logically (e.g. models, then scanner, then checker)
- [ ] Commit messages have a body, not just a title — point to `leapp-commit-message-assist` for help
- [ ] Remind the developer to consider adding a Jira/issue reference if none is present

### Test coverage (cite `leapp-unit-tests`)

- [ ] Important behavior is tested (especially inhibitor and report paths), not just "no exception"
- [ ] Assertions check produced models, report flags, or outcomes
- [ ] Missing test cases called out as concrete scenarios, not just "add more tests"

## Reference

- [Coding guidelines](https://leapp-repository.readthedocs.io/latest/contributing/coding-guidelines.html)
- [Phases overview](https://leapp-repository.readthedocs.io/latest/upgrade-architecture-and-workflow/phases-overview.html)
