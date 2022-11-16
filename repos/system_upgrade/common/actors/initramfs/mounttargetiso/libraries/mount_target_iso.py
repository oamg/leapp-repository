import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TargetOSInstallationImage, TargetUserSpaceInfo


def mount_target_iso():
    target_os_iso = next(api.consume(TargetOSInstallationImage), None)
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    if not target_os_iso:
        return

    mountpoint = os.path.join(target_userspace_info.path, target_os_iso.mountpoint[1:])
    if not os.path.exists(mountpoint):
        # The target userspace container exists, however, the mountpoint has been removed during cleanup.
        os.makedirs(mountpoint)
    try:
        run(['mount', target_os_iso.path, mountpoint])
    except CalledProcessError as err:
        # Unlikely, since we are checking that the ISO is mountable and located on a persistent partition. This would
        # likely mean that either the fstab entry for the partition points uses a different device that the one that
        # was mounted during pre-reboot, or the fstab has been tampered with before rebooting. Either way, there is
        # nothing at this point how we can recover.
        msg = 'Failed to mount the target RHEL ISO file containing RPMs to install during the upgrade.'
        raise StopActorExecutionError(message=msg, details={'details': '{0}'.format(err)})
