from leapp import reporting
from leapp.libraries.stdlib import api, format_list
from leapp.models import StorageInfo

# Stratis filesystems are exposed as symlinks under /dev/stratis/<pool>/<fs>
_STRATIS_DEVICE_PREFIX = '/dev/stratis/'

# Entries referencing a Stratis filesystem by UUID= are recognisable only by
# the systemd unit taking care of the pool activation, which is required to be
# present in the mount options.
_STRATIS_MNTOPS_MARKERS = ('stratis-fstab-setup', 'stratisd-min.service')


def process():
    stratis_entries = []
    for storage_info in api.consume(StorageInfo):
        for entry in storage_info.fstab:
            if _is_stratis_entry(entry):
                stratis_entries.append(entry.fs_file)

    if stratis_entries:
        _inhibit_upgrade(stratis_entries)
        return

    api.current_logger().debug('No Stratis filesystem detected in /etc/fstab.')


def _is_stratis_entry(entry):
    if entry.fs_spec.startswith(_STRATIS_DEVICE_PREFIX):
        return True
    return any(marker in entry.fs_mntops for marker in _STRATIS_MNTOPS_MARKERS)


def _inhibit_upgrade(stratis_entries):
    title = 'Use of Stratis detected. Upgrade cannot proceed'
    summary = (
        'Stratis is a supported storage management solution, however it is not'
        ' currently supported by the leapp in-place upgrade. The initramfs used'
        ' during the upgrade does not contain stratisd, so Stratis pools cannot'
        ' be activated and the configured filesystems cannot be mounted. This'
        ' would break the upgrade process and it could also prevent the system'
        ' from booting afterwards.'
        ' The following mount points are backed by Stratis filesystems:{}'
        .format(format_list(stratis_entries))
    )
    remediation_hint = (
        'Unmount the Stratis filesystems and comment out the related entries'
        ' in /etc/fstab before the upgrade. The filesystems can be mounted'
        ' again once the upgrade is finished. If the data has to be available'
        ' during the upgrade, migrate it to a storage backend supported by the'
        ' in-place upgrade.'
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
