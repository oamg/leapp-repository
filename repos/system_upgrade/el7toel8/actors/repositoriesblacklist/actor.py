from leapp.actors import Actor
from leapp.models import RepositoriesBlacklisted, RepositoriesFacts
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RepositoriesBlacklist(Actor):
    """
    Generate list of Repositories ID that should be ignored by Leapp during upgrade process
    """

    name = 'repositories_blacklist'
    consumes = (RepositoriesFacts,)
    produces = (RepositoriesBlacklisted,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def _is_repo_enabled(self, repoid):
        for repos in self.consume(RepositoriesFacts):
            for repo_file in repos.repositories:
                for repo in repo_file.data:
                    if repo.repoid == repoid and repo.enabled:
                        return True
        return False

    def process(self):
        # blacklist crb repo <=> optional repo is not enabled
        if not self._is_repo_enabled('rhel-7-server-optional-rpms'):
            self.log.info("The optional repository is not enabled. Add the CRB repository to the blacklist.")
            self.produce(RepositoriesBlacklisted(
                repoids=['codeready-builder-for-rhel-8-x86_64-rpms']))
