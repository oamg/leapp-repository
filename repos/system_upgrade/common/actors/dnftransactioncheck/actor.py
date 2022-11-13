from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import (
    DNFPluginTask,
    DNFWorkaround,
    FilteredRpmTransactionTasks,
    StorageInfo,
    TargetOSInstallationImage,
    TargetUserSpaceInfo,
    UsedTargetRepositories,
    XFSPresence
)
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class DnfTransactionCheck(Actor):
    """
    This actor tries to solve the RPM transaction to verify the all package dependencies can be successfully resolved.
    """

    name = 'dnf_transaction_check'
    consumes = (
        DNFPluginTask,
        DNFWorkaround,
        FilteredRpmTransactionTasks,
        StorageInfo,
        TargetOSInstallationImage,
        TargetUserSpaceInfo,
        UsedTargetRepositories,
        XFSPresence,
    )
    produces = ()
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def process(self):
        xfs_info = next(self.consume(XFSPresence), XFSPresence())
        storage_info = next(self.consume(StorageInfo), StorageInfo())
        used_repos = self.consume(UsedTargetRepositories)
        plugin_info = list(self.consume(DNFPluginTask))
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        target_iso = next(self.consume(TargetOSInstallationImage), None)

        if target_userspace_info:
            dnfplugin.perform_transaction_check(
                tasks=tasks, used_repos=used_repos, target_userspace_info=target_userspace_info,
                xfs_info=xfs_info, storage_info=storage_info, plugin_info=plugin_info, target_iso=target_iso
            )
