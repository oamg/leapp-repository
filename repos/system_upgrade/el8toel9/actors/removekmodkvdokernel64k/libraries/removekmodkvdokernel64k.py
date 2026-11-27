from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.common.kernel import KernelPageSize
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, KernelInfo, RpmTransactionTasks

KMOD_KVDO_PKG = 'kmod-kvdo'


def process():
    if not architecture.matches_architecture(architecture.ARCH_ARM64):
        return

    if not has_package(DistributionSignedRPM, KMOD_KVDO_PKG):
        return

    kernel_info = next(api.consume(KernelInfo), None)
    if not kernel_info:
        raise StopActorExecutionError('Could not retrieve KernelInfo message.')

    if kernel_info.page_size != KernelPageSize.PAGE_SIZE_64K:
        return

    api.current_logger().info(
        'Removing %s from the upgrade transaction because it conflicts with'
        ' kernel-64k which is required for 64k page-size parity on aarch64.',
        KMOD_KVDO_PKG
    )
    api.produce(RpmTransactionTasks(to_remove=[KMOD_KVDO_PKG]))

    reporting.create_report([
        reporting.Title(
            'kmod-kvdo package will be removed during the upgrade'
        ),
        reporting.Summary(
            'The kmod-kvdo package will be removed during the upgrade because'
            ' it conflicts with kernel-64k, the 64 KB page-size kernel required'
            ' on this aarch64 system. RHEL 9 builds of kmod-kvdo declare'
            ' Conflicts: kernel-64k and cannot be upgraded together with that'
            ' kernel.'
            '\n'
            'Removing kmod-kvdo does not remove existing VDO volumes. On RHEL 9,'
            ' VDO is provided by the dm-vdo kernel module and managed through LVM.'
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS]),
    ])
