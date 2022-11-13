from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import (
    BootContent,
    DNFPluginTask,
    DNFWorkaround,
    FilteredRpmTransactionTasks,
    RHUIInfo,
    StorageInfo,
    TargetOSInstallationImage,
    TargetUserSpaceInfo,
    TransactionDryRun,
    UsedTargetRepositories,
    XFSPresence
)
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class DnfDryRun(Actor):
    """
    Actor that invokes DNF to download the RPMs required for the upgrade transaction.

    This actor uses the rhel-upgrade plugin to perform the download of RPM for the transaction and performing the
    transaction test, that is something like a dry run trying to determine the success of the upgrade.
    """

    name = 'dnf_dry_run'
    consumes = (
        BootContent,
        DNFPluginTask,
        DNFWorkaround,
        FilteredRpmTransactionTasks,
        RHUIInfo,
        StorageInfo,
        TargetOSInstallationImage,
        TargetUserSpaceInfo,
        UsedTargetRepositories,
        XFSPresence,
    )
    produces = (TransactionDryRun,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        xfs_info = next(self.consume(XFSPresence), XFSPresence())
        storage_info = next(self.consume(StorageInfo), StorageInfo())
        used_repos = self.consume(UsedTargetRepositories)
        plugin_info = list(self.consume(DNFPluginTask))
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        rhui_info = next(self.consume(RHUIInfo), None)
        target_iso = next(self.consume(TargetOSInstallationImage), None)
        on_aws = bool(rhui_info and rhui_info.provider == 'aws')

        dnfplugin.perform_dry_run(
            tasks=tasks, used_repos=used_repos, target_userspace_info=target_userspace_info,
            xfs_info=xfs_info, storage_info=storage_info, plugin_info=plugin_info, on_aws=on_aws,
            target_iso=target_iso,
        )
        self.produce(TransactionDryRun())
