from leapp import reporting
from leapp.libraries.stdlib import api, format_list
from leapp.models import StorageInfo

# Stratis filesystems are exposed as symlinks under /dev/stratis/<pool>/<fs>
_STRATIS_DEVICE_PREFIX = '/dev/stratis/'

# Entries referencing a Stratis filesystem by UUID= are recognisable only by
# the systemd unit taking care of the pool activation, which is required to be
# present in the mount options.
_STRATIS_MNTOPS_MARKERS = ('stratis-fstab-setup',)


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
