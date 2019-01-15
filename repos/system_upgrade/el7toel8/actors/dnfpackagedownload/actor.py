from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, UsedTargetRepositories
from leapp.tags import DownloadPhaseTag, IPUWorkflowTag


class DnfPackageDownload(Actor):
    """
    Actor that invokes DNF to download the RPMs required for the upgrade transaction.

    This actor uses the rhel-upgrade plugin to perform the download of RPM for the transaction and performing the
    transaction test, that is something like a dry run trying to determine the success of the upgrade.
    """

    name = 'dnf_package_download'
    consumes = (UsedTargetRepositories, FilteredRpmTransactionTasks, TargetUserSpaceInfo)
    produces = ()
    tags = (IPUWorkflowTag, DownloadPhaseTag)

    def process(self):
        dnfplugin.perform_rpm_download()
