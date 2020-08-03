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

    def process(self):
        # fmt: off
        used_target_repos = next(self.consume(UsedTargetRepositories)).repos
        target_repos = next(self.consume(TMPTargetRepositoriesFacts)).repositories
        # fmt: on
        target_repo_id_to_url_map = {
            repo.repoid: repo.baseurl
            for repofile in target_repos
            for repo in repofile.data
            if repo.baseurl
        }
        if any(
            target_repo_id_to_url_map[repo.repoid].startswith("file:")
            for repo in used_target_repos
        ):
            warn_msg = (
                "Local repository found (baseurl starts with file:///). "
                "Currently leapp is not supporting this option."
            )
            self.log.warning(warn_msg)
            reporting.create_report(
                [
                    reporting.Title("Local repository identified"),
                    reporting.Summary(warn_msg),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Tags([reporting.Tags.REPOSITORY]),
                    reporting.Flags([reporting.Flags.INHIBITOR]),
                    reporting.Remediation(
                        hint=(
                            "By using Apache HTTP Server you can expose "
                            "your local repository via http. For details "
                            "see external link."
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
