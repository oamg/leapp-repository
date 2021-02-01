from leapp.actors import Actor
from leapp.libraries.actor import checknonmountboots390
from leapp.models import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNonMountBootS390(Actor):
    """
    Inhibits on s390 when /boot is NOT on a separate partition.

    Due to some problems, if /boot is not on a separate partition, leapp is deleting the content of /boot.
    To avoid this from happening, we are inhibiting the upgrade process until this problem has been solved.
    """

    name = 'check_non_mount_boot_s390'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checknonmountboots390.perform_check()
