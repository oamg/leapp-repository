import platform

from leapp.actors import Actor
from leapp.models import (CustomTargetRepositories, RepositoriesBlacklisted,
                          RepositoriesFacts, RepositoriesMap,
                          RHELTargetRepository, SkippedRepositories,
                          TargetRepositories, UsedRepositories)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SetupTargetRepos(Actor):
    """
    Produces list of repositories that should be available to be used by the upgrade process.

    Based on the enabled RHEL 7 repositories, it produces a list of RHEL 8 repositories to be enabled for the upgrade.
    It additionaly processes requests to use custom repositories to be used in the upgrade transaction.
    """

    name = 'setuptargetrepos'
    consumes = (CustomTargetRepositories,
                RepositoriesMap,
                RepositoriesFacts,
                RepositoriesBlacklisted,
                UsedRepositories)
    produces = (TargetRepositories, SkippedRepositories)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    custom_repos = []
    enabled_repos = set()
    mapping_of_repositories = []  # list of RepositoryMap
    mapped_rhel7_repoids = set()  # enabled RHEL 7 repos that have been successfully mapped to the RHEL 8 ones
    target_repos = []
    used_repos = {}

    def process(self):
        self.get_custom_repos()
        self.get_enabled_repos()
        self.get_mapping_of_repositories()
        self.get_target_repos()
        self.process_skipped_repos()
        self.filter_out_blacklisted_repos()
        self.produce_target_repos_msg()

    def get_custom_repos(self):
        """Consume message with repositories that other actors want to be used in the upgrade transaction."""
        for custom_repos_msg in self.consume(CustomTargetRepositories):
            for custom_repo in custom_repos_msg.repos:
                self.custom_repos.append(custom_repo)

    def get_enabled_repos(self):
        """Consume message with repositories enabled on the system."""
        for repos in self.consume(RepositoriesFacts):
            for repo_file in repos.repositories:
                for repo in repo_file.data:
                    if repo.enabled:
                        self.enabled_repos.add(repo.repoid)

    def get_mapping_of_repositories(self):
        """Get the mapping of RHEL 7 to RHEL 8 repos."""
        for mapping_of_repositories_msg in self.consume(RepositoriesMap):
            for repo_mapping in mapping_of_repositories_msg.repositories:
                self.mapping_of_repositories.append(repo_mapping)

    def get_target_repos(self):
        """Get RHEL 8 repos to enable based on the mapping of the enabled RHEL 7 repos."""
        for repo_mapping in self.mapping_of_repositories:
            # Check if the repo mapping architecture matches the current system architecture
            if platform.machine() != repo_mapping.arch:
                continue

            if repo_mapping.from_id in self.enabled_repos:
                self.mapped_rhel7_repoids.add(repo_mapping.from_id)
                self.target_repos.append(RHELTargetRepository(repoid=repo_mapping.to_id))

    def process_skipped_repos(self):
        """Send a message about any used repo that is missing in the repo mapping."""
        self.get_used_repos()
        not_mapped_repos = [
            used_repo for used_repo in self.used_repos if used_repo not in self.mapped_rhel7_repoids]

        if not_mapped_repos:
            pkgs = self.get_pkgs_installed_from_not_mapped_repos(not_mapped_repos)
            self.produce(SkippedRepositories(repos=list(not_mapped_repos), packages=list(pkgs)))

    def get_used_repos(self):
        """Get those enabled repositories from which at least one RH-signed package is currently installed."""
        for used_repos_msg in self.consume(UsedRepositories):
            for used_repo in used_repos_msg.repositories:
                self.used_repos[used_repo.repoid] = used_repo.packages

    def get_pkgs_installed_from_not_mapped_repos(self, not_mapped_repos):
        pkgs = set()
        for repo in not_mapped_repos:
            pkgs.update(self.used_repos[repo])
        return pkgs

    def filter_out_blacklisted_repos(self):
        """Remove blacklisted repositories from those to be used in the upgrade transaction."""
        blacklisted_repos = set()
        for blacklist in self.consume(RepositoriesBlacklisted):
            blacklisted_repos.update(blacklist.repoids)
        self.target_repos = [repo for repo in self.target_repos if repo.repoid not in blacklisted_repos]
        self.custom_repos = [repo for repo in self.custom_repos if repo.repoid not in blacklisted_repos]

    def produce_target_repos_msg(self):
        self.produce(TargetRepositories(
            rhel_repos=self.target_repos,
            custom_repos=self.custom_repos,
        ))
