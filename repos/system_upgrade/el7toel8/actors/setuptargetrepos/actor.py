import platform

from leapp.actors import Actor
from leapp.models import (CustomTargetRepository, RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMap,
                          RepositoriesSetupTasks, RHELTargetRepository, SkippedRepositories, TargetRepositories,
                          UsedRepositories)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


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
    produces = (TargetRepositories, SkippedRepositories)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
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

                mapped_repos.add(repo_map.from_repoid)
                if repo_map.from_repoid in enabled_repos:
                    rhel_repos.append(RHELTargetRepository(repoid=repo_map.to_repoid))

        skipped_repos = enabled_repos.difference(mapped_repos)

        used = {}
        for used_repos in self.consume(UsedRepositories):
            for used_repo in used_repos.repositories:
                used[used_repo.repository] = used_repo.packages
                for repo in repo_file.data:
                    enabled_repos.add(repo.repoid)

        skipped_repos = skipped_repos.intersection(set(used.keys()))

        if skipped_repos:
            pkgs = set()
            for repo in skipped_repos:
                pkgs.update(used[repo])
            self.produce(SkippedRepositories(repos=list(skipped_repos), packages=list(pkgs)))

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
