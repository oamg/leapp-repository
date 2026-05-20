from leapp import reporting
from leapp.libraries.stdlib import api, format_list
from leapp.models import StorageInfo

API_FS_EXPECTED_TYPES = {
    '/dev/shm': {'tmpfs'},
    '/dev/pts': {'devpts'},
    '/dev/mqueue': {'mqueue'},
    '/dev/hugepages': {'hugetlbfs'},
    '/proc': {'proc'},
    '/sys': {'sysfs'},
    '/sys/fs/cgroup': {'cgroup', 'cgroup2', 'tmpfs'},
    '/sys/fs/selinux': {'selinuxfs'},
    '/sys/kernel/debug': {'debugfs'},
    '/sys/kernel/security': {'securityfs'},
    '/run': {'tmpfs'},
    '/run/lock': {'tmpfs'},
}


def check_fstab_api_fs_override():
    """
    Check fstab entries targeting pseudo-filesystem mountpoints for invalid sources or types.

    An entry is flagged if its mount point is a known pseudo-filesystem path and
    either the filesystem type or the source device does not match the expected
    virtual filesystem set. The 'none' pseudo-source is also accepted.
    """
    storage_info = next(api.consume(StorageInfo), None)
    if not storage_info:
        return

    bad_entries = []
    for entry in storage_info.fstab:
        mount_point = entry.fs_file
        if mount_point != '/':
            mount_point = mount_point.rstrip('/')

        expected = API_FS_EXPECTED_TYPES.get(mount_point)
        if not expected:
            continue

        if entry.fs_vfstype not in expected or entry.fs_spec not in (expected | {'none'}):
            bad_entries.append(entry)

    if not bad_entries:
        return

    entries_text = format_list(
        [e.fs_file for e in bad_entries],
    )

    reporting.create_report([
        reporting.Title(
            'Detected invalid entries in /etc/fstab for pseudo-filesystem mountpoints'
        ),
        reporting.Summary(
            'Detected /etc/fstab entries that incorrectly define pseudo-filesystem '
            'mountpoints. These mountpoints (e.g. /proc, /sys, /dev/shm, /run) are '
            'managed by the kernel and systemd, and their fstab entries must use the '
            'correct virtual filesystem type and source. Defining them with a block '
            'device (via /dev/*, UUID=, LABEL=, etc.) or a wrong filesystem type is '
            'invalid. Such configurations were common on RHEL 6 and earlier and are '
            'typically ignored during normal boot. However, during the upgrade the '
            'system applies fstab entries as configured, which may lead to failures.\n'
            'Problematic entries: {}'.format(entries_text)
        ),
        reporting.Remediation(
            hint=(
                'Remove or correct the problematic entries in /etc/fstab. If an entry '
                'is required (e.g. to set specific mount options for compliance), ensure '
                'both the source and the filesystem type match the expected virtual '
                "filesystem (e.g. 'tmpfs /dev/shm tmpfs defaults 0 0').\n"
                'After editing, run "mount -a" to verify.'
            )
        ),
        reporting.RelatedResource('file', '/etc/fstab'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.INHIBITOR]),
    ])
