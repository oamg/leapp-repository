import platform

from leapp.actors import Actor
from leapp.libraries.common import reporting
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import CustomTargetRepository, RHELTargetRepository, RepositoriesBlacklisted, \
    RepositoriesFacts, RepositoriesMap, RepositoriesSetupTasks, TargetRepositories, \
    UsedRepositories
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class SetupTargetRepos(Actor):
    """
    Produces list of repositories that should be available to be used by Upgrade process.

    Based on current set of Red Hat Enterprise Linux repositories, produces the list of target
    repositories. Additionaly process request to use custom repositories during the upgrade
    transaction.
    """

    name = 'setuptargetrepos'
    consumes = (CustomTargetRepository,
                RepositoriesSetupTasks,
                RepositoriesMap,
                RepositoriesFacts,
                RepositoriesBlacklisted,
                UsedRepositories)
    produces = (TargetRepositories, Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)


    def report_skipped_repos(self, repos, pkgs):
        title = 'Some enabled RPM repositories are unknown to Leapp'
        summary_data = []
        summary_data.append('The following repositories with Red Hat-signed packages are unknown to Leapp:')
        summary_data.extend(['- ' + r for r in repos])
        summary_data.append('And the following packages installed from those repositories may not be upgraded:')
        summary_data.extend(['- ' + p for p in pkgs])
        summary = '\n'.join(summary_data)
        reporting.report_with_remediation(
            title=title,
            summary=summary,
            remediation='You can file a request to add this repository to the scope of in-place upgrades '
                        'by filing a support ticket',
            severity='low')

        if is_verbose():
            self.log.info('\n'.join([title, summary]))


    def process(self):
        # TODO: Think about Beta and Alpha repositories. How will we tell we
        # + want to go to GA, Alpha, Beta, ... repos?

        custom_repos = []
        for repo in self.consume(CustomTargetRepository):
            custom_repos.append(repo)

        enabled_repos = set()
        for repos in self.consume(RepositoriesFacts):
            for repo_file in repos.repositories:
                for repo in repo_file.data:
                    if repo.enabled:
                        enabled_repos.add(repo.repoid)

        rhel_repos = []
        mapped_repos = set()
        for repos_map in self.consume(RepositoriesMap):
            for repo_map in repos_map.repositories:
                # Check if repository map architecture matches system architecture
                if platform.machine() != repo_map.arch:
                    continue

                mapped_repos.add(repo_map.from_id)
                if repo_map.from_id in enabled_repos:
                    rhel_repos.append(RHELTargetRepository(repoid=repo_map.to_id))

        skipped_repos = enabled_repos.difference(mapped_repos)

        used = {}
        for used_repos in self.consume(UsedRepositories):
            for used_repo in used_repos.repositories:
                used[used_repo.repository] = used_repo.packages
                for repo in repo_file.data:
                    enabled_repos.add(repo.repoid)

        skipped_repos = skipped_repos.intersection(used.keys())

        if skipped_repos:
            pkgs = []
            for repo in skipped_repos:
                pkgs.extend(used[repo])
            self.report_skipped_repos(skipped_repos, pkgs)

        for task in self.consume(RepositoriesSetupTasks):
            for repo in task.to_enable:
                rhel_repos.append(RHELTargetRepository(repoid=repo))

        repos_blacklisted = set()
        for blacklist in self.consume(RepositoriesBlacklisted):
            repos_blacklisted.update(blacklist.repoids)
        rhel_repos = [repo for repo in rhel_repos if repo.repoid not in repos_blacklisted]
        custom_repos = [repo for repo in custom_repos if repo.repoid not in repos_blacklisted]

        self.produce(TargetRepositories(
            rhel_repos=rhel_repos,
            custom_repos=custom_repos,
        ))

        # TODO: Some informational messages would be added for the report and
        # + logs, so we and user will know exactly what is going on.

        return
