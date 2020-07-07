from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import (
    DNFPluginTask,
    FilteredRpmTransactionTasks,
    RHUIInfo,
    StorageInfo,
    TargetUserSpaceInfo,
    UsedTargetRepositories,
    XFSPresence,
)
from leapp.tags import DownloadPhaseTag, IPUWorkflowTag


class DnfPackageDownload(Actor):
    """
    Actor that invokes DNF to download the RPMs required for the upgrade transaction.

    This actor uses the rhel-upgrade plugin to perform the download of RPM for the transaction and performing the
    transaction test, that is something like a dry run trying to determine the success of the upgrade.
    """

    name = 'dnf_package_download'
    consumes = (
        DNFPluginTask,
        FilteredRpmTransactionTasks,
        RHUIInfo,
        StorageInfo,
        TargetUserSpaceInfo,
        UsedTargetRepositories,
        XFSPresence,
    )
    produces = ()
    tags = (IPUWorkflowTag, DownloadPhaseTag)

    def process(self):
        xfs_info = next(self.consume(XFSPresence), XFSPresence())
        storage_info = next(self.consume(StorageInfo), StorageInfo())
        used_repos = self.consume(UsedTargetRepositories)
        plugin_info = list(self.consume(DNFPluginTask))
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        rhui_info = next(self.consume(RHUIInfo), None)
        on_aws = bool(rhui_info and rhui_info.provider == 'aws')

        dnfplugin.perform_rpm_download(
            tasks=tasks, used_repos=used_repos, target_userspace_info=target_userspace_info,
            xfs_info=xfs_info, storage_info=storage_info, plugin_info=plugin_info, on_aws=on_aws
        )
