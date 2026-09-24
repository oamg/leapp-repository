---
name: leapp-commit-message-assist
description: >-
  Draft and improve commit titles/bodies and PR descriptions for leapp-repository.
  Use when the user asks for commit message help, PR description text, or wording
  for a review-ready submission.
---

# Commit and PR text (advise only)

## Scope and hard rules

This skill **only** helps with wording and structure:

- Commit titles and bodies
- PR description text

**Do not** (unless the user explicitly requests it):

- Run `git commit`, `git push`, or create a PR (`gh pr create`)
- Rebase, squash, or rewrite history on the user's behalf
- Assume a multi-commit series is needed for a small change

Default output: propose the text; let the user apply it.

For code quality review of a diff/PR, use `skills/leapp-code-review/` instead.
For writing actors/tests, use `skills/leapp-actor-dev/` and `skills/leapp-unit-tests/`.

## Workflow

1. Identify the change:
   - By default, inspect staged changes with `git diff --cached`.
   - If nothing is staged, inspect the latest commit with `git log -1` and `git show HEAD`.
   - If the user provides a commit, revision, or path, use that instead.

2. Understand the problem and solution. Focus on *why*, not just changed files.

3. Draft the commit message using the format below.

4. For a PR description, use the full branch diff (`git diff <base>...HEAD`) and the PR template below.

## Commit message format

Every commit ready for review needs a title and a body. WIP/fixup commits that will be squashed before review may omit the body.

### Title

- Imperative mood, concise (≤72 chars)
- Optional scope prefix for path-specific changes: `el8toel9: actorname: Summary`
- Do not use `[N/M]` series prefixes unless the user explicitly requests them

### Body

- Explain what problem is solved and how
- Enough context that readers need not read the full diff
- If the user provides a Jira/issue reference, place it as the last line using one of the formats below

```
Jira: RHEL-XXXXX
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

Scoped commit:

```
el8toel9: checkkernelarm: Install 64k kernel

On RHEL 8 for ARM, the default kernel is 64k (pagesize) and there is
no 4k alternative. On RHEL 9 the default kernel is 4k, but for 64k
the kernel-64k RPMs need to be installed.

Jira: RHEL-111860
```

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
