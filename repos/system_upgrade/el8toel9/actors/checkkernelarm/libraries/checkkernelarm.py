from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import KernelInfo, RpmTransactionTasks


def process():
    if not architecture.matches_architecture(architecture.ARCH_ARM64):
        # Nothing to do.
        return

    kernel_info = next(api.consume(KernelInfo), None)
    if not kernel_info:
        raise StopActorExecutionError('Could not retrieve KernelInfo message.')

    target_pkgs = kernel_lib.get_target_kernel_pkg_names(
        kernel_info.type,
        kernel_info.page_size,
        api.current_actor().configuration.architecture
    )

    api.current_logger().debug(
        "Register expected target kernel RPMs for installation on ARM."
    )
    api.produce(RpmTransactionTasks(
        to_install=sorted(list(target_pkgs)))
    )
