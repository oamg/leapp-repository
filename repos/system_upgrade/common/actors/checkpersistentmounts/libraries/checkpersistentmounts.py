from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import StorageInfo


def inhibit_upgrade_due_non_persistent_mount(mountpoint):
    summary = (
        'Leapp detected that the {0} mountpoint is mounted, with no corresponding entry in /etc/fstab. '
        'The upgrade process cannot continue with {0} mounted in non-persistent fashion, '
        'as Leapp needs this mount to be available after a reboot.'
    )

    hint = (
        'Add {0} mount entry to /etc/fstab'
    )

    reporting.create_report([
        reporting.Title(
            'Detected partitions mounted in a non-persistent fashion, preventing a successful in-place upgrade.'
        ),
        reporting.Summary(summary.format(mountpoint)),
        reporting.Remediation(hint=hint.format(mountpoint)),
        reporting.RelatedResource('file', '/etc/fstab'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])


def check_mount_is_persistent(storage_info, mountpoint):
    """Check if mountpoint is mounted in persistent fashion"""

    mount_entry_exists = any(me.mount == mountpoint for me in storage_info.mount)
    fstab_entry_exists = any(fe.fs_file == mountpoint for fe in storage_info.fstab)

    if mount_entry_exists and not fstab_entry_exists:
        inhibit_upgrade_due_non_persistent_mount(mountpoint)


def check_persistent_mounts():
    storage_info = next(api.consume(StorageInfo), None)
    if storage_info:
        check_mount_is_persistent(storage_info, '/var/lib/leapp')
