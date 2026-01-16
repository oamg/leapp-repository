from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RpmTransactionTasks

KERNEL_RT_PKG = 'kernel-rt'
KERNEL_RT_CORE_PKG = 'kernel-rt-core'


def process():
    pkgs = next(api.consume(DistributionSignedRPM), None)
    if not pkgs:
        raise StopActorExecutionError("Did not receive DistributionSignedRPM message.")

    has_kernel_rt = any(pkg.name == KERNEL_RT_PKG for pkg in pkgs.items)
    if has_kernel_rt:
        api.current_logger().debug(
            'Removing {} package as a workaround for problems with '
            'finding its best upgrade candidate.'.format(KERNEL_RT_PKG)
        )
        api.produce(RpmTransactionTasks(to_remove=[KERNEL_RT_PKG], to_upgrade=[KERNEL_RT_CORE_PKG]))
