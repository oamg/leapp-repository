from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import StorageInfo

# man 5 xfs
REMOVED_XFS_OPTIONS = set([
    # removed from kernel in 4.0
    'nodelaylog',
    'delaylog',
    'ihashsize',
    'irixsgid',
    'osyncisdsync',
    'osyncisosync',
    # removed from kernel in 4.19
    'nobarrier',
    'barrier',
])


def _get_storage_data():
    storage = next(api.consume(StorageInfo), None)
    if not storage:
        raise StopActorExecutionError('The StorageInfo message is not available.')
    if not storage.fstab:
        raise StopActorExecutionError('Data from the /etc/fstab file is missing.')
    return storage


def process():
    storage = _get_storage_data()
    used_removed_options = set()
    for entry in storage.fstab:
        if entry.fs_vfstype == 'xfs':
            # NOTE: some opts could have a value, like ihashsize=4096 - we want
            # just the name of the option (that's why the double-split)
            options = set([opt.split('=')[0] for opt in entry.fs_mntops.split(',')])
            used_removed_options.update(options.intersection(REMOVED_XFS_OPTIONS))

    if not used_removed_options:
        return

    list_separator_fmt = '\n    - '
    reporting.create_report([
        reporting.Title('Deprecated XFS mount options present in FSTAB.'),
        reporting.Summary(
            'Some XFS mount options are not supported on RHEL 8 and prevent'
            ' system from booting correctly if any of the reported XFS options are used.'
            ' filesystem:{}{}.'.format(
                list_separator_fmt,
                list_separator_fmt.join(list(REMOVED_XFS_OPTIONS)))),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.RelatedResource('file', '/etc/fstab'),
        reporting.Remediation(hint=(
            'Drop the following mount options from the /etc/fstab file for any'
            ' XFS filesystem: {}.'.format(', '.join(used_removed_options)))),
    ])
