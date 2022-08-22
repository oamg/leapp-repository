from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import StorageInfo


def inhibit_upgrade_due_var_with_noexec(mountpoint, found_in_fstab=False):
    summary = (
        'Leapp detected that the {0} mountpoint is mounted with the "noexec" option, '
        'which prevents binaries necessary for the upgrade from being executed. '
        'The upgrade process cannot continue with {0} mounted using the "noexec" option.'
    )

    if found_in_fstab:
        hint = (
            'Temporarily remove the "noexec" option from {0} entry in /etc/fstab until the system is upgraded, '
            'and remount the partition without the "noexec" option.'
        )
        related_resource = [reporting.RelatedResource('file', '/etc/fstab')]
    else:
        hint = (
            'Remount {0} without the noexec option and make sure the change is persistent'
            'during the entire in-place upgrade process.'
        )
        related_resource = []

    reporting.create_report([
        reporting.Title(
            'Detected partitions mounted with the "noexec" option, preventing a successful in-place upgrade.'
        ),
        reporting.Summary(summary.format(mountpoint)),
        reporting.Remediation(hint=hint.format(mountpoint)),
        reporting.RelatedResource('file', '/etc/fstab'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ] + related_resource)


def find_mount_entry_with_mountpoint(mount_entries, mountpoint):
    for mount_entry in mount_entries:
        if mount_entry.mount == mountpoint:
            return mount_entry
    return None


def find_fstab_entry_with_mountpoint(fstab_entries, mountpoint):
    for fstab_entry in fstab_entries:
        if fstab_entry.fs_file == mountpoint:
            return fstab_entry
    return None


def check_noexec_on_var(storage_info):
    """Check for /var or /var/lib being mounted with noexec mount option."""

    # Order of checking is important as mount options on /var/lib override those on /var
    mountpoints_to_check = ('/var/lib/leapp', '/var/lib', '/var')
    for mountpoint in mountpoints_to_check:
        fstab_entry = find_fstab_entry_with_mountpoint(storage_info.fstab, mountpoint)
        if fstab_entry and 'noexec' in fstab_entry.fs_mntops.split(','):
            inhibit_upgrade_due_var_with_noexec(fstab_entry.fs_file, found_in_fstab=True)
            return  # Do not check further as present mounts would likely reflect fstab

    # Make sure present mountpoints don't contain noexec as well - user might have fixed noexec in fstab
    # but did not remount the partition, or, less likely, mounted the partition without creating a fstab entry
    for mountpoint in mountpoints_to_check:
        mount_entry = find_mount_entry_with_mountpoint(storage_info.mount, mountpoint)
        if mount_entry and 'noexec' in mount_entry.options.split(','):
            inhibit_upgrade_due_var_with_noexec(mount_entry.mount, found_in_fstab=False)
            return


def check_mount_options():
    for storage_info in api.consume(StorageInfo):
        check_noexec_on_var(storage_info)
