import os

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RaidInfo

PROC_MDSTAT = '/proc/mdstat'


def _has_active_arrays():
    """
    Parse /proc/mdstat and return True if at least one active array exists.

    An active array line looks like:
        md0 : active raid1 sda1[0] sdb1[1]
    Lines containing ' : active ' indicate assembled arrays.
    """
    if not os.path.isfile(PROC_MDSTAT):
        return False
    with open(PROC_MDSTAT) as f:
        for line in f:
            if ' : active ' in line:
                return True
    return False


def process():
    if not has_package(DistributionSignedRPM, 'mdadm'):
        api.current_logger().debug('The mdadm package is not installed. Skipping.')
        return

    if not _has_active_arrays():
        api.current_logger().debug('No active MD arrays found in %s.', PROC_MDSTAT)
        return

    api.current_logger().info('Detected active mdadm software RAID arrays.')
    api.produce(RaidInfo(mdraid_used=True))
