from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import XFSInfoFacts

RHEL_9_TO_10_BACKUP_RESTORE_LINK = 'https://red.ht/rhel_9_to_10_backup_restore_xfs'

FMT_LIST_SEPARATOR = '\n    - '


def _formatted_list_output(input_list, sep=FMT_LIST_SEPARATOR):
    return ['{}{}'.format(sep, item) for item in input_list]


def process():
    xfs_info_facts = _get_xfs_info_facts()

    invalid_bigtime = []
    invalid_crc = []
    for xfs_info in xfs_info_facts.mountpoints:
        if not _has_valid_bigtime(xfs_info):
            api.current_logger().debug(
                'Mountpoint {} has invalid bigtime'.format(xfs_info.mountpoint)
            )
            invalid_bigtime.append(xfs_info.mountpoint)

        if not _has_valid_crc(xfs_info):
            api.current_logger().debug(
                'Mountpoint {} has invalid crc'.format(xfs_info.mountpoint)
            )
            invalid_crc.append(xfs_info.mountpoint)

    if invalid_bigtime or invalid_crc:
        _inhibit_upgrade(invalid_bigtime, invalid_crc)

        return

    api.current_logger().debug('All XFS system detected are valid.')


def _get_xfs_info_facts():
    msgs = api.consume(XFSInfoFacts)

    xfs_info_facts = next(msgs, None)
    if xfs_info_facts is None:
        raise StopActorExecutionError('Could not retrieve XFSInfoFacts!')

    if next(msgs, None):
        api.current_logger().warning(
            'Unexpectedly received more than one XFSInfoFacts message.')

    return xfs_info_facts


def _has_valid_bigtime(xfs_info):
    return xfs_info.meta_data.bigtime == '1'


def _has_valid_crc(xfs_info):
    return xfs_info.meta_data.crc == '1'


def _inhibit_upgrade(invalid_bigtime, invalid_crc):
    if invalid_bigtime:
        _report_bigtime(invalid_bigtime)

    if invalid_crc:
        _inhibit_crc(invalid_crc)


def _report_bigtime(invalid_bigtime):
    title = 'Detected XFS filesystems without bigtime feature.'
    summary = (
        'The XFS v5 filesystem format introduced the "bigtime" feature in RHEL 9,'
        ' to support timestamps beyond the year 2038. XFS filesystems that'
        ' do not have the "bigtime" feature enabled remain vulnerable to timestamp'
        ' overflow issues. It is recommended to enable this feature on all'
        ' XFS filesystems to ensure long-term compatibility and prevent potential'
        ' failures.'
        ' Following XFS file systems have not enabled the "bigtime" feature:{}'
        .format(''.join(_formatted_list_output(invalid_bigtime)))
    )

    # NOTE(pstodulk): This will affect any system which upgraded from RHEL 8 so
    # it is clear that such FS will have to be modified offline e.g. from
    # initramfs - and that we speak about significant number of systems. So
    # this should be improved yet. E.g. to update the initramfs having
    # xfs_admin inside and working:
    # # dracut -I "/usr/sbin/xfs_admin /usr/bin/expr" -f
    # Note that it seems that it could be done without xfs_admin, using xfs_db
    # only - which is present already.
    remediation_hint = (
        'Enable the "bigtime" feature on XFS v5 filesystems using the command:'
        '\n\txfs_admin -O bigtime=1 <filesystem_device>\n\n'
        'Note that for older XFS v5 filesystems this step can only be done'
        ' offline right now (i.e. without the filesystem mounted).'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.ExternalLink(
            title='XFS supports bigtime feature',
            url='https://red.ht/rhel-9-xfs-bigtime',
        ),
        reporting.Severity(reporting.Severity.LOW),
    ])


def _inhibit_crc(invalid_crc):
    title = 'Detected XFS filesystems incompatible with target kernel.'
    summary = (
        'XFS v4 format has been deprecated and it has been removed from'
        ' the target kernel. Such filesystems cannot be mounted by target'
        ' system kernel and so the upgrade cannot proceed successfully.'
        ' Following XFS filesystems have v4 format:{}'
        .format(''.join(_formatted_list_output(invalid_crc)))
    )
    remediation_hint = (
        'Migrate XFS v4 filesystems to new XFS v5 format.'
        ' For filesystems hosting data, perform a back up, reformat, and restore procedure.'
        ' Refer to official documentation for details.'
        ' For filesystems hosting the system a clean installation is recommended instead.'
    )

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Remediation(hint=remediation_hint),
        reporting.ExternalLink(
            title='Backing up an XFS file system',
            url='https://red.ht/rhel-9-xfs-backup',
        ),
        reporting.ExternalLink(
            title='Restoring an XFS file system from backup',
            url='https://red.ht/rhel-9-xfs-restore-from-backup',
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])
