---
name: leapp-code-review
description: >-
  Review leapp-repository code changes and pull requests for upgrade safety,
  actor design, inhibitors, tests, and project conventions. Use when reviewing
  a PR, a branch, a diff, or when the user asks for a code review.
---

# Code review (leapp-repository)

## Scope

Review **code and design** of a change set. Produce actionable feedback with severity.

Do **not** restate or re-teach rules from other skills. When a finding matches a known rule, cite the skill (or `AGENTS.md`) and focus on why this diff violates it.

| Concern | Canonical source — do not duplicate |
|---------|-------------------------------------|
| Actor structure, phases, placement, constraints, Python matrix | `skills/leapp-actor-dev/` + `AGENTS.md` |
| How to write / structure unit tests | `skills/leapp-unit-tests/` |
| How to run lint/tests | `skills/leapp-test-runner/` |
| Commit titles, bodies, PR description wording | `skills/leapp-commit-pr-text/` |

Do **not** push, merge, or create PRs as part of a review unless the user explicitly asks.

## Workflow

1. Establish the change set: PR URL, `git diff <base>...HEAD`, or files the user names. Prefer the full PR/branch diff, not only the latest commit.
2. Skim PR description and commit messages for intent (flag missing context; do not rewrite them here — point to `leapp-commit-pr-text`).
3. Walk the review-focused checklist below. For actor/test conventions, load the linked skill only when needed to judge a specific finding.
4. Report findings using the output format. Lead with blockers.
5. State confidence when uncertain: `[Certain]` / `[Likely]` / `[Speculative]`.

## Output format

```markdown
## Summary
<1–3 sentences: what the change does and overall readiness>

## Findings

### Blockers
- **[area]** <issue> — <why it matters> — <concrete fix hint> (cite skill if applicable)

### Major
- ...

### Minor / nits
- ...

### Questions / assumptions
- ...

## What looks good
- <brief positives worth keeping>

## Suggested checks
- <commands or scenarios — prefer pointing at `leapp-test-runner` rather than listing every make target>
```

Severity guide:

| Level | Meaning |
|-------|---------|
| **Blocker** | Wrong upgrade behavior, missing inhibitor, broken message flow, ChecksPhase system I/O, forbidden APIs, untested critical path, Python incompat that will fail CI |
| **Major** | Design smell vs project patterns, weak tests, unclear reporting, risky edge cases |
| **Minor** | Style, naming, small clarity — skip pure preference nits |

Prefer fewer high-signal comments over exhaustive style notes.

## Review checklist (review-only)

These are judgment calls for the diff. Convention details live in the linked skills.

### Upgrade safety (primary focus)

- [ ] Blocking conditions inhibit when the upgrade must not proceed (`reporting.Groups.INHIBITOR` or project-equivalent)
- [ ] Non-blocking issues are reported appropriately (not silent)
- [ ] Report text is actionable for operators (problem + remediation)
- [ ] Edge cases covered: missing files, empty/missing messages, partial configs, unexpected arches/versions
- [ ] External command failures handled (`CalledProcessError`; `OSError` when the binary may be absent)
- [ ] Reboot-/env-safe where relevant (`LEAPP_` + `get_env`, not bare env that dies across reboots)

### Design fitness (cite `leapp-actor-dev` / `AGENTS.md` on failure)

- [ ] Facts collection vs decide/inhibit/modify are in the right actors and phases
- [ ] Consumed/produced models match actual `api.consume` / `api.produce` usage; message flow is forward-safe
- [ ] No unnecessary new models/utilities that already exist elsewhere
- [ ] Scope matches the stated problem; no unrelated drive-by edits

### Test adequacy (cite `leapp-unit-tests` on failure)

- [ ] Critical behavior is covered (especially inhibitor/report paths), not only “no exception”
- [ ] Assertions check produced models / report flags / outcomes
- [ ] Obvious gaps called out as concrete missing cases (not “add more tests”)

## Common defects → where the rule lives

| Defect | Cite |
|--------|------|
| Logic only in `actor.py` | `leapp-actor-dev` |
| Scanner + checker fused | `AGENTS.md` / `leapp-actor-dev` |
| System I/O in ChecksPhase | `leapp-actor-dev` |
| `subprocess` usage | `leapp-actor-dev` |
| Wrong Python syntax/API for repo | `leapp-actor-dev` Python compatibility |
| Untested library / inhibitor path | `leapp-unit-tests` |
| Weak commit/PR prose | `leapp-commit-pr-text` (one-liner only) |

## Depth tips

- Load `leapp-actor-dev` only when phase/placement/constraint judgment needs the full rule.
- Load `leapp-unit-tests` only when proposing concrete missing test cases.
- Do not paste large excerpts from those skills into the review.

## Reference

- [Coding guidelines](https://leapp-repository.readthedocs.io/latest/contributing/coding-guidelines.html)
- [Phases overview](https://leapp-repository.readthedocs.io/latest/upgrade-architecture-and-workflow/phases-overview.html)
