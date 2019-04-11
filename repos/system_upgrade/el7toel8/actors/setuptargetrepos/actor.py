import platform

from leapp.actors import Actor
from leapp.models import CustomTargetRepository, RHELTargetRepository, RepositoriesBlacklisted, \
    RepositoriesFacts, RepositoriesMap, RepositoriesSetupTasks, TargetRepositories
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class SetupTargetRepos(Actor):
    """
    Produces list of repositories that should be available to be used by Upgrade process.

    Based on current set of Red Hat Enterprise Linux repositories, produces the list of target
    repositories. Additionaly process request to use custom repositories during the upgrade
    transaction.
    """

    name = 'setuptargetrepos'
    consumes = (CustomTargetRepository, RepositoriesSetupTasks, RepositoriesMap, RepositoriesFacts, RepositoriesBlacklisted)
    produces = (TargetRepositories,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        # TODO: Think about Beta and Alpha repositories. How will we tell we
        # + want to go to GA, Alpha, Beta, ... repos?

        custom_repos = []
        for repo in self.consume(CustomTargetRepository):
            custom_repos.append(repo)

        enabled_repos = []
        for repos in self.consume(RepositoriesFacts):
            for repo_file in repos.repositories:
                for repo in repo_file.data:
                    enabled_repos.append(repo.repoid)

        rhel_repos = []
        for repos_map in self.consume(RepositoriesMap):
            for repo_map in repos_map.repositories:
                # Check if repository map architecture matches system architecture
                if platform.machine() != repo_map.arch:
                    continue

                if repo_map.from_id in enabled_repos:
                    rhel_repos.append(RHELTargetRepository(repoid=repo_map.to_id))

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
