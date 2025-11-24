# Commits and pull requests (PRs)
## PR description
The description should contain information about all introduced changes:
* What has been changed
* How it has been changed
* The reason for the change
* How could people try/test the PR
* Reference to a Jira ticket, Github issue, ... if applicable

Good description provides all information for readers without the need to
read the code. Note that reviewers can decline to review the PR with a poor
description.

## Commit messages
When your pull-request is ready to be reviewed, every commit needs to include
a title and a body continuing a description of the change --- what problem is
being solved and how. The end of the commit body should contain Jira issue
number (if applicable), GitHub issue that is being fixed, etc.:
```
  Commit title

  Commit message body on multiple lines

  Jira-ref: <ticket-number>
```

Note that good commit message should provide information in similar way like
the PR description. Poorly written commit messages can block the merge of PR
or proper review.

## Granularity of commits
The granularity of commits depends strongly on the problem being solved. However,
a large number of small commits is typically undesired. If possible, aim a
Git history such that commits can be reverted individually, without requiring reverting
numerous other dependent commits in order to get the `main` branch into a working state.

Note that commits fixing problems of other commits in the PR are expected to be
squashed before the final review and merge of the PR. Using of `git commit --fixup ...`
and `git commit --squash ...` commands can help you to prepare such commits
properly in advance and make the rebase later easier using `git rebase -i --autosquash`.
We suggest you to get familiar with these commands as it can make your work really
easier. Note that when you are starting to get higher number of such fixing commits
in your PR, it's good practice to use the rebase more often. High numbers of such
commits could make the final rebase more tricky in the end. So your PR should not
have more than 15 commits at any time.

## Create a separate git branch for your changes
TBD
