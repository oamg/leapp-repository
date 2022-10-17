import os

from leapp.libraries.stdlib import api, run
from leapp.models import TargetOSInstallationImage, TargetUserSpaceInfo


def mount_target_iso():
    target_os_iso = next(api.consume(TargetOSInstallationImage), None)
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    if not target_os_iso:
        return

    # TODO(mhecko) Handle possible errors
    mountpoint = os.path.join(target_userspace_info.path, target_os_iso.mountpoint[1:])
    run(['mount', target_os_iso.path, mountpoint])
