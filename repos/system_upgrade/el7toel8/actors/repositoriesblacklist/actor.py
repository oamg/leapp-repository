from leapp.actors import Actor
from leapp.libraries.actor.repositoriesblacklist import process
from leapp.models import (
    CustomTargetRepository,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMap,
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RepositoriesBlacklist(Actor):
    """
    Exclude target repositories provided by Red Hat without support.

    Conditions to exclude:
    - there are not such repositories already enabled on the source system
      (e.g. "Optional" repositories)
    - such repositories are not required for the upgrade explicitly by the user
      (e.g. via the --enablerepo option or via the /etc/leapp/files/leapp_upgrade_repositories.repo file)

    E.g. CRB repository is provided by Red Hat but it is without the support.
    """

    name = "repositories_blacklist"
    consumes = (
        CustomTargetRepository,
        RepositoriesFacts,
        RepositoriesMap,
    )
    produces = (RepositoriesBlacklisted, Report)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
