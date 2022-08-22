from leapp.actors import Actor
from leapp.models import (
    InstalledRedHatSignedRPM,
    RepositoriesFacts,
    UsedRepositories,
    UsedRepository
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class UsedRepositoriesScanner(Actor):
    """
    Scan used enabled repositories

    Based on lists of installed RPM packages and enabled RPM repositories, check which packages
    were installed from each repository.
    """

    name = 'used_repository_scanner'
    consumes = (InstalledRedHatSignedRPM, RepositoriesFacts)
    produces = (UsedRepositories,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        enabled_repos = []
        for repos in self.consume(RepositoriesFacts):
            for repo_file in repos.repositories:
                for repo in repo_file.data:
                    if repo.enabled:
                        enabled_repos.append(repo.repoid)

        installed_pkgs = []
        for rpm_pkgs in self.consume(InstalledRedHatSignedRPM):
            installed_pkgs.extend(rpm_pkgs.items)

        used_repos = {}
        for pkg in installed_pkgs:
            if pkg.repository in enabled_repos:
                used_repos.setdefault(pkg.repository, []).append(pkg.name)

        result = UsedRepositories()
        for repo, pkgs in used_repos.items():
            result.repositories.append(UsedRepository(repository=repo, packages=pkgs))
        self.produce(result)
