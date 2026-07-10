---
name: leapp-commit-pr-text
description: >-
  Draft and improve commit titles/bodies and PR descriptions for leapp-repository.
  Use when the user asks for commit message help, PR description text, squashing
  advice, or wording for a review-ready submission. Does not create commits or PRs.
---

# Commit and PR text (advise only)

## Scope and hard rules

This skill **only** helps with wording and structure:

- Commit titles and bodies
- PR description text
- Advice on commit granularity / what to squash before review

**Do not** (unless the user explicitly requests it):

- Run `git commit`, `git push`, or create a PR (`gh pr create`)
- Rebase, squash, or rewrite history on the user's behalf
- Assume a multi-commit series is needed for a small change

Default output: propose the text; let the user apply it.

For code quality review of a diff/PR, use `skills/leapp-code-review/` instead.
For how to write actors/tests, use `skills/leapp-actor-dev/` and `skills/leapp-unit-tests/`.

## Workflow

1. Inspect the change set the user cares about (`git diff`, `git log`, or the files they point at).
2. Infer the problem solved and the approach — prefer *why* over a file list.
3. Draft commit message(s) and/or the PR description using the formats below.
4. If messages are weak (title-only, no body, no ticket when one exists), say what to fix and offer rewritten text.

## Commit message format

Every commit ready for review needs a title and a body. WIP/fixup commits that will be squashed before review may omit the body.

### Title

- Imperative mood, concise (≤72 chars)
- Optional scope prefix for path-specific changes: `el8toel9: actorname: Summary`
- Series prefix `[N/M]` only when the PR is a deliberate multi-commit progression

### Body

- Explain what problem is solved and how
- Enough context that readers need not read the full diff
- Last line: Jira/issue reference when applicable; omit when none exists (tooling, CI, docs-only)

```
Jira: RHEL-XXXXX
```

or

```
Jira-ref: RHEL-XXXXX
```

### Examples

Single commit:

```
Add machine-id validation actors for in-place upgrade

Introduced a scanner/checker actor pair that verifies /etc/machine-id
exists and contains a valid 32-character hexadecimal identifier.
The upgrade is inhibited if the file is missing or malformed, as
a valid machine-id is required by systemd and the target userspace
container creation.

Jira: RHEL-50161
```

Series commit:

```
[3/9] targetcontentresolver: RepositoriesBlacklisted: use it as task

Refactored RepositoriesBlacklisted to operate as a task model consumed
by the target content resolver instead of being evaluated independently.
This centralizes message consumption and simplifies dependency tracking.

Jira: RHEL-115867
```

Scoped commit:

```
el8toel9: checkkernelarm: Install 64k kernel

On RHEL 8 for ARM, the default kernel is 64k (pagesize) and there is
no 4k alternative. On RHEL 9 the default kernel is 4k, but for 64k
the kernel-64k RPMs need to be installed.

JIRA: RHEL-111860
```

## Commit granularity (advice only)

- Prefer one meaningful logical unit per commit; each should be independently revertable without breaking `main`.
- Prefer fewer well-structured commits over many trivial ones.
- Fixups should be squashed before review (`git commit --fixup` / `--squash`, then rebase with autosquash) — **advise** the commands; do not run them unless asked.
- Keep total commit count (including unsquashed fixups) under 15.
- For multi-actor features, logical grouping is fine (e.g. models, then scanner, then checker) — do not invent a large series for a small change.

## PR description template

```markdown
## The reason for the change

<motivation: the problem being solved or requirement being addressed>

## What has been changed

<concise summary of the introduced changes>

## How it has been changed

<implementation approach and key design decisions>

## How to try/test the PR

<steps for reviewers to try/verify — commands, scenarios, or expected output>

## Reference to a Jira ticket

- Jira: RHEL-XXXXX
```

Fill every section from the diff. Reviewers may decline poorly described PRs.

## Reference

- [PR and commit guidelines](https://leapp-repository.readthedocs.io/latest/contributing/pr-guidelines.html)
