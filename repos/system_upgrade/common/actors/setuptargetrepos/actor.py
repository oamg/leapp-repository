from leapp.actors import Actor
from leapp.libraries.actor import setuptargetrepos
from leapp.models import (
    CustomTargetRepository,
    InstalledRPM,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RHUIInfo,
    SkippedRepositories,
    TargetRepositories,
    UsedRepositories
)
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SetupTargetRepos(Actor):
    """
    Produces list of repositories that should be available to be used during IPU process.

    The list of expected target repositories is produced based on:
      * required custom target repositories,
      * discovered enabled repositories,
      * repositories from which originates the installed content,
      * and the system distribution.

    The list of repositories can be additionally affected in case of RHEL by
    required channel (e.g. eus) or by detected use of RHUI.
    """

    name = 'setuptargetrepos'
    consumes = (CustomTargetRepository,
                InstalledRPM,
                RepositoriesSetupTasks,
                RepositoriesMapping,
                RepositoriesFacts,
                RepositoriesBlacklisted,
                RHUIInfo,
                UsedRepositories)
    produces = (TargetRepositories, SkippedRepositories)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        setuptargetrepos.process()
