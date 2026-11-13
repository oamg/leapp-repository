from leapp.actors import Actor
from leapp.libraries.actor import removekmodkvdokernel64k
from leapp.models import DistributionSignedRPM, KernelInfo, RpmTransactionTasks
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class RemoveKmodKvdoOnKernel64k(Actor):
    """
    Remove kmod-kvdo from the upgrade transaction on aarch64 with 64k page size.

    The kmod-kvdo package (standalone VDO kernel module) conflicts with the
    kernel-64k package required on this architecture. All RHEL 9 builds of
    kmod-kvdo declare Conflicts: kernel-64k, making it impossible to upgrade
    the package alongside the 64k page-size kernel.

    This does not affect VDO volume availability. In RHEL 9, VDO is integrated
    into the kernel via the dm-vdo module and managed through LVM. Existing VDO
    volumes must be converted to LVM management before upgrading (handled by the
    check_vdo actor).
    """

    name = 'remove_kmod_kvdo_kernel_64k'
    consumes = (DistributionSignedRPM, KernelInfo)
    produces = (RpmTransactionTasks, Report)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        removekmodkvdokernel64k.process()
