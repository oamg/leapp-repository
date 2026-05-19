from leapp.actors import Actor
from leapp.libraries.actor.targetcontentresolver import process
from leapp.models import (
    ConsumedDataAsset,
    CustomTargetRepository,
    DistributionSignedRPM,
    EnabledModules,
    InstalledRPM,
    PESRpmTransactionTasks,
    RepositoriesBlacklisted,
    RepositoriesBlocklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RHUIInfo,
    RpmTransactionTasks,
    SkippedRepositories,
    TargetRepositories,
    UsedRepositories
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(RepositoriesBlacklisted)
class TargetContentResolver(Actor):
    """
    Resolve the complete set of target repositories and RPM transaction tasks for the upgrade.

    This actor consolidates four steps that were previously separate actors:
    1. Load the repository mapping (repomap.json) and produce RepositoriesMapping.
    2. Determine which target repositories should be excluded (e.g. unsupported CRB repos).
    3. Process PES events (pes-events.json) to compute package changes and
       produce PESRpmTransactionTasks.
    4. Determine the final list of target repositories to enable, producing
       TargetRepositories and SkippedRepositories.
    """

    name = 'target_content_resolver'
    consumes = (
        CustomTargetRepository,
        DistributionSignedRPM,
        EnabledModules,
        InstalledRPM,
        RepositoriesFacts,
        RepositoriesSetupTasks,
        RHUIInfo,
        RpmTransactionTasks,
        UsedRepositories,
    )
    produces = (
        ConsumedDataAsset,
        PESRpmTransactionTasks,
        Report,
        RepositoriesBlacklisted,
        RepositoriesBlocklisted,
        RepositoriesMapping,
        SkippedRepositories,
        TargetRepositories,
    )
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        process()
