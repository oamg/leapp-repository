from leapp import reporting
from leapp.actors import Actor
from leapp.models import TargetOSInstallationImage, TMPTargetRepositoriesFacts, UsedTargetRepositories
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(TMPTargetRepositoriesFacts)
class LocalReposInhibit(Actor):
    """Inhibits the upgrade if local repositories were found."""

    name = "local_repos_inhibit"
    consumes = (
        UsedTargetRepositories,
        TargetOSInstallationImage,
        TMPTargetRepositoriesFacts,
    )
    produces = (Report,)
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def collect_target_repoids_with_local_url(self, used_target_repos, target_repos_facts, target_iso):
        """Collects all repoids that have a local (file://) URL.

        UsedTargetRepositories doesn't contain baseurl attribute. So gathering
        them from model TMPTargetRepositoriesFacts.
        """
        used_target_repoids = set(repo.repoid for repo in used_target_repos.repos)
        iso_repoids = set(iso_repo.repoid for iso_repo in target_iso.repositories) if target_iso else set()

        target_repofile_data = (repofile.data for repofile in target_repos_facts.repositories)

        local_repoids = []
        for repo_data in target_repofile_data:
            for target_repo in repo_data:
                # Check only in repositories that are used and are not provided by the upgrade ISO, if any
                if target_repo.repoid not in used_target_repoids or target_repo.repoid in iso_repoids:
                    continue

                # Repo fields potentially containing local URLs have different importance, check based on their prio
                url_field_to_check = target_repo.mirrorlist or target_repo.metalink or target_repo.baseurl or ''

                if url_field_to_check.startswith("file://"):
                    local_repoids.append(target_repo.repoid)
        return local_repoids

    def process(self):
        used_target_repos = next(self.consume(UsedTargetRepositories), None)
        target_repos_facts = next(self.consume(TMPTargetRepositoriesFacts), None)
        target_iso = next(self.consume(TargetOSInstallationImage), None)

        if not used_target_repos or not target_repos_facts:
            return

        local_repoids = self.collect_target_repoids_with_local_url(used_target_repos, target_repos_facts, target_iso)
        if local_repoids:
            suffix, verb = ("y", "has") if len(local_repoids) == 1 else ("ies", "have")
            local_repoids_str = ", ".join(local_repoids)

            warn_msg = ("The following local repositor{suffix} {verb} been found: {local_repoids} "
                        "(their baseurl starts with file:///). Currently leapp does not support this option.")
            warn_msg = warn_msg.format(suffix=suffix, verb=verb, local_repoids=local_repoids_str)
            self.log.warning(warn_msg)

            reporting.create_report(
                [
                    reporting.Title("Local repositor{suffix} detected".format(suffix=suffix)),
                    reporting.Summary(warn_msg),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.REPOSITORY]),
                    reporting.Groups([reporting.Groups.INHIBITOR]),
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
                            "https://red.ht/ipu-customisation-repos-known-issues"
                        ),
                    ),
                ]
            )
