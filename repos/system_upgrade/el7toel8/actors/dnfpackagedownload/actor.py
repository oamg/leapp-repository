from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, UsedTargetRepositories, XFSPresence
from leapp.tags import DownloadPhaseTag, IPUWorkflowTag


class DnfPackageDownload(Actor):
    """
    Actor that invokes DNF to download the RPMs required for the upgrade transaction.

    This actor uses the rhel-upgrade plugin to perform the download of RPM for the transaction and performing the
    transaction test, that is something like a dry run trying to determine the success of the upgrade.
    """

    name = 'dnf_package_download'
    consumes = (UsedTargetRepositories, FilteredRpmTransactionTasks, TargetUserSpaceInfo, XFSPresence)
    produces = ()
    tags = (IPUWorkflowTag, DownloadPhaseTag)

    def process(self):
        presence = next(self.consume(XFSPresence), XFSPresence())
        xfs_present = presence.present and presence.without_ftype
        used_repos = self.consume(UsedTargetRepositories)
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)

        dnfplugin.perform_rpm_download(tasks=tasks, used_repos=used_repos, target_userspace_info=target_userspace_info,
                                       xfs_present=xfs_present)
