import os

from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    KernelCmdline,
    RaidInfo,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeKernelCmdlineArgTasks,
)

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


def _emit_rdmd_undesired_for_upgrade_cmdline():
    """
    Identify rd.md.uuid args on the source kernel cmdline and request their
    removal from the upgrade boot entry.

    The upgrade initramfs assembles mdraid arrays from mdadm configuration.
    Dracut's rd.md.uuid mechanism limits which arrays are activated during
    boot. We want all relevant arrays to be available during the upgrade,
    so rd.md.uuid args must not be carried over to the upgrade kernel cmdline.
    """
    cmdline = next(api.consume(KernelCmdline), None)
    if not cmdline:
        api.current_logger().debug('No KernelCmdline message received, nothing to do.')
        return

    rdmd_args = [arg for arg in cmdline.parameters if arg.key == 'rd.md.uuid']

    if not rdmd_args:
        api.current_logger().debug('No rd.md.uuid args found on the source kernel cmdline.')
        return

    api.current_logger().debug(
        'Requesting removal of rd.md.uuid args from the upgrade kernel cmdline: %s',
        ['{}={}'.format(a.key, a.value) for a in rdmd_args],
    )
    api.produce(UpgradeKernelCmdlineArgTasks(to_remove=rdmd_args))

    # When installing the target kernel RPM, the cmdline is copied from the booted system.
    # As we remove the rd.md.uuid args, we would accidentally remove them also from the
    # target entry. Therefore, we add them back in here.
    api.produce(TargetKernelCmdlineArgTasks(to_add=rdmd_args))


def process():
    raid_info = next(api.consume(RaidInfo), None)
    if not raid_info or not raid_info.mdraid_used:
        return

    copy_files = [CopyFile(src=path) for path in _mdadm_config_paths_present()]
    if not copy_files:
        api.current_logger().warning(
            'mdadm software RAID is in use but no mdadm configuration was found under: %s',
            ', '.join(MDADM_CONFIG_PATHS),
        )
    else:
        api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files))

    _emit_rdmd_undesired_for_upgrade_cmdline()
