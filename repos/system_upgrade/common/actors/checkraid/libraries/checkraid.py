import os

from leapp.libraries.stdlib import api
from leapp.models import CopyFile, RaidInfo, TargetUserSpaceUpgradeTasks

# Host paths for mdadm configuration (see mdadm.conf(5) FILES section).
MDADM_CONFIG_PATHS = (
    '/etc/mdadm.conf',
    '/etc/mdadm.conf.d',
    '/etc/mdadm/mdadm.conf',
    '/etc/mdadm/mdadm.conf.d',
)


def _mdadm_config_paths_present():
    for path in MDADM_CONFIG_PATHS:
        if os.path.isfile(path) or os.path.isdir(path):
            yield path


def process():
    raid_info = next(api.consume(RaidInfo), None)
    if not raid_info or not raid_info.md_arrays:
        return

    copy_files = [CopyFile(src=path) for path in _mdadm_config_paths_present()]
    if not copy_files:
        api.current_logger().warning(
            'mdadm software RAID is in use but no mdadm configuration was found under: %s',
            ', '.join(MDADM_CONFIG_PATHS),
        )
    else:
        api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files))
