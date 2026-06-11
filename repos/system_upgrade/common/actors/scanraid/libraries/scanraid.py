import re

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DistributionSignedRPM, MDArray, RaidInfo

MDADM_SCAN_CMD = ['mdadm', '--detail', '--scan', '--verbose']
UUID_PATTERN = re.compile(r'UUID=([0-9a-fA-F:]+)')


def _scan_md_array_uuids():
    try:
        result = run(MDADM_SCAN_CMD)
    except CalledProcessError as err:
        api.current_logger().warning('Failed to scan mdadm arrays: %s', err)
        return []

    uuids = []
    for line in result['stdout'].splitlines():
        if not line.startswith('ARRAY '):
            continue
        match = UUID_PATTERN.search(line)
        if match:
            uuids.append(match.group(1))

    return uuids


def process():
    if not has_package(DistributionSignedRPM, 'mdadm'):
        api.current_logger().debug('The mdadm package is not installed. Skipping.')
        return

    uuids = _scan_md_array_uuids()
    if not uuids:
        api.current_logger().debug('No active mdadm software RAID arrays found.')
        return

    api.current_logger().info('Detected active mdadm software RAID arrays.')
    api.produce(RaidInfo(md_arrays=[MDArray(UUID=uuid) for uuid in uuids]))
