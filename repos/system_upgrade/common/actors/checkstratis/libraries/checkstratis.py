import os

from leapp import reporting
from leapp.libraries.stdlib import api, format_list
from leapp.models import LiveModeConfig, StorageInfo, TargetUserSpaceUpgradeTasks

# Stratis filesystems are exposed as symlinks under /dev/stratis/<pool>/<fs>
_STRATIS_DEVICE_PREFIX = '/dev/stratis/'

# Entries referencing a Stratis filesystem by UUID= are recognisable only by
# the systemd unit taking care of the pool activation, which is required to be
# present in the mount options.
_STRATIS_MNTOPS_MARKERS = ('stratis-fstab-setup',)

# Packages that have to be present in the target userspace so that Stratis
# pools can be activated and their filesystems mounted during a live mode
# upgrade. The fstab entries request the start of stratisd themselves, so it is
# sufficient to make the daemon available.
_STRATIS_LIVEMODE_PACKAGES = ['stratisd']


def process():
    stratis_entries = []
    for storage_info in api.consume(StorageInfo):
        for entry in storage_info.fstab:
            if _is_stratis_entry(entry):
                stratis_entries.append(entry.fs_file)

    if not stratis_entries:
        api.current_logger().debug('No Stratis filesystem detected in /etc/fstab.')
        return

    if _is_stratis_supported_by_livemode():
        livemode_config = next(api.consume(LiveModeConfig), None)
        image_stratis_mount = _find_stratis_mount_for_path(livemode_config.squashfs_fullpath, stratis_entries)
        if image_stratis_mount:
            _inhibit_upgrade_image_on_stratis(livemode_config.squashfs_fullpath, image_stratis_mount)
            return

        api.current_logger().info(
            'Stratis filesystems detected in /etc/fstab, but the upgrade is using the live mode.'
            ' Requesting Stratis packages to be installed into the target userspace instead of'
            ' inhibiting the upgrade.'
        )
        api.produce(TargetUserSpaceUpgradeTasks(install_rpms=_STRATIS_LIVEMODE_PACKAGES))
        return

    _inhibit_upgrade(stratis_entries)


def _is_stratis_entry(entry):
    if entry.fs_spec.startswith(_STRATIS_DEVICE_PREFIX):
        return True
    return any(marker in entry.fs_mntops for marker in _STRATIS_MNTOPS_MARKERS)


def _is_stratis_supported_by_livemode():
    """
    Can Stratis filesystems be mounted during the upgrade using the live mode?

    Unlike the regular upgrade, the live mode upgrade runs from a full userspace
    into which stratisd can be installed, allowing the Stratis pools to be
    activated and their filesystems mounted during the upgrade.
    """
    livemode_config = next(api.consume(LiveModeConfig), None)
    return bool(livemode_config and livemode_config.is_enabled)


def _find_stratis_mount_for_path(path, stratis_mountpoints):
    """
    Return the Stratis mount point that the given file path resides on, or None.

    Starting from the file's parent directory, the ancestor directories are
    walked upwards until an actual mount point is found. That mount point is the
    filesystem the file resides on. If it is backed by Stratis it is returned;
    otherwise the file lives on a non-Stratis filesystem (which may still be
    nested under a Stratis mount) and None is returned.
    """
    normalized_stratis = {os.path.normpath(mountpoint) for mountpoint in stratis_mountpoints}

    current = os.path.dirname(os.path.normpath(path))
    while True:
        if os.path.ismount(current):
            # This is the filesystem the file resides on. Report it only if it is
            # backed by Stratis; a non-Stratis mount here means the file does not
            # live on Stratis even if a Stratis mount exists further up the tree.
            return current if current in normalized_stratis else None
        parent = os.path.dirname(current)
        if parent == current:
            # Reached the filesystem root without it being reported as a mount.
            return None
        current = parent


def _inhibit_upgrade(stratis_entries):
    title = 'Use of Stratis detected. Upgrade cannot proceed'
    summary = (
        'The Stratis storage management solution is unsupported for in-place'
        ' upgrades. The upgrade will fail because the following Stratis filesystems'
        f' are unable to be mounted during the upgrade: {format_list(stratis_entries)}'
    )
    remediation_hint = (
        'Unmount the Stratis filesystems and comment out the related entries'
        ' in /etc/fstab before the upgrade or use live mode.'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('file', '/etc/fstab'),
    ])


def _inhibit_upgrade_image_on_stratis(image_path, stratis_mountpoint):
    title = 'The live mode upgrade image is located on a Stratis filesystem. Upgrade cannot proceed'
    summary = (
        'The live mode upgrade image (squashfs) is configured to be stored at'
        ' {image_path}, which resides on the Stratis filesystem mounted at'
        ' {mountpoint}. The upgrade image has to be loaded early during boot,'
        ' before stratisd is available and the Stratis pools are activated.'
        ' An image stored on a Stratis filesystem therefore cannot be accessed'
        ' at that point and the upgrade would fail.'
        .format(image_path=image_path, mountpoint=stratis_mountpoint)
    )
    remediation_hint = (
        'Change the leapp live mode configuration so that the upgrade image is'
        ' placed on a filesystem that is not backed by Stratis.'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])
