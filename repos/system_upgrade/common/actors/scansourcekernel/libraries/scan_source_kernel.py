import itertools

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.config.version import get_source_version
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, KernelInfo


def scan_source_kernel():
    uname_r = api.current_actor().configuration.kernel
    installed_rpms = [msg.items for msg in api.consume(InstalledRedHatSignedRPM)]
    installed_rpms = list(itertools.chain(*installed_rpms))

    kernel_type = kernel_lib.determine_kernel_type_from_uname(get_source_version(), uname_r)
    kernel_pkg_info = kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)

    kernel_pkg_id = (kernel_pkg_info.name, kernel_pkg_info.version, kernel_pkg_info.release, kernel_pkg_info.arch)
    kernel_pkg = None
    for pkg in installed_rpms:
        pkg_id = (pkg.name, pkg.version, pkg.release, pkg.arch)
        if kernel_pkg_id == pkg_id:
            kernel_pkg = pkg
            break

    if not kernel_pkg:
        raise StopActorExecutionError(message='Unable to identify package providing the booted kernel.')

    kernel_info = KernelInfo(pkg=kernel_pkg, type=kernel_type, uname_r=uname_r)
    api.produce(kernel_info)
