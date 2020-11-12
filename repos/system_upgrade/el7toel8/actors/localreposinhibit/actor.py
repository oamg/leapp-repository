from leapp import reporting
from leapp.actors import Actor
from leapp.models import TMPTargetRepositoriesFacts, UsedTargetRepositories
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(TMPTargetRepositoriesFacts)
class LocalReposInhibit(Actor):
    """Inhibits the upgrade if local repositories were found."""

    name = "local_repos_inhibit"
    consumes = (
        UsedTargetRepositories,
        TMPTargetRepositoriesFacts,
    )
    produces = (Report,)
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def file_baseurl_in_use(self):
        """Check if any of target repos is local.

        UsedTargetRepositories doesn't contain baseurl attribute. So gathering
        them from model TMPTargetRepositoriesFacts.
        """
        used_target_repos = next(self.consume(UsedTargetRepositories)).repos
        target_repos = next(self.consume(TMPTargetRepositoriesFacts)).repositories
        target_repo_id_to_url_map = {
            repo.repoid: repo.mirrorlist or repo.metalink or repo.baseurl or ""
            for repofile in target_repos
            for repo in repofile.data
        }
        return any(
            target_repo_id_to_url_map[repo.repoid].startswith("file:")
            for repo in used_target_repos
        )

    def process(self):
        if self.file_baseurl_in_use():
            warn_msg = (
                "Local repository found (baseurl starts with file:///). "
                "Currently leapp does not support this option."
            )
            self.log.warning(warn_msg)
            reporting.create_report(
                [
                    reporting.Title("Local repository detected"),
                    reporting.Summary(warn_msg),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.REPOSITORY, reporting.Groups.INHIBITOR]),
                    reporting.Remediation(
                        hint=(
                            "By using Apache HTTP Server you can expose "
                            "your local repository via http. See the linked "
                            "article for details. "
                        )
                    ),
                    reporting.ExternalLink(
                        title=(
                            "Customizing your Red Hat Enterprise Linux "
                            "in-place upgrade"
                        ),
                        url=(
                            "https://access.redhat.com/articles/4977891/"
                            "#repos-known-issues"
                        ),
                    ),
                ]
            )
