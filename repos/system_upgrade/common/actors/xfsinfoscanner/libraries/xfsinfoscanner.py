import os
import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import StorageInfo, XFSInfo, XFSInfoFacts, XFSPresence


def scan_xfs():
    storage_info_msgs = api.consume(StorageInfo)
    storage_info = next(storage_info_msgs, None)

    if list(storage_info_msgs):
        api.current_logger().warning(
            'Unexpectedly received more than one StorageInfo message.'
        )

    fstab_data = set()
    mount_data = set()
    if storage_info:
        fstab_data = scan_xfs_fstab(storage_info.fstab)
        mount_data = scan_xfs_mount(storage_info.mount)

    mountpoints = fstab_data | mount_data

    xfs_infos = {}
    for mountpoint in mountpoints:
        content = read_xfs_info(mountpoint)
        if content is None:
            continue

        xfs_info = parse_xfs_info(content)
        xfs_infos[mountpoint] = xfs_info

    mountpoints_ftype0 = [
        mountpoint
        for mountpoint in xfs_infos
        if is_without_ftype(xfs_infos[mountpoint])
    ]

    # By now, we only have XFS mountpoints and check whether or not it has
    # ftype = 0
    api.produce(XFSPresence(
        present=len(mountpoints) > 0,
        without_ftype=len(mountpoints_ftype0) > 0,
        mountpoints_without_ftype=mountpoints_ftype0,
    ))

    api.produce(
        XFSInfoFacts(
            mountpoints=[
                XFSInfo(
                    mountpoint=mountpoint,
                    meta_data=xfs_infos[mountpoint]['meta-data'],
                    data=xfs_infos[mountpoint]['data'],
                    naming=xfs_infos[mountpoint]['naming'],
                    log=xfs_infos[mountpoint]['log'],
                    realtime=xfs_infos[mountpoint]['realtime'],
                )
                for mountpoint in xfs_infos
            ]
        )
    )


def scan_xfs_fstab(data):
    mountpoints = set()
    for entry in data:
        if entry.fs_vfstype == "xfs":
            mountpoints.add(entry.fs_file)

    return mountpoints


def scan_xfs_mount(data):
    mountpoints = set()
    for entry in data:
        if entry.tp == "xfs":
            mountpoints.add(entry.mount)

    return mountpoints


def read_xfs_info(mp):
    if not is_mountpoint(mp):
        return None

    try:
        result = run(['/usr/sbin/xfs_info', '{}'.format(mp)], split=True)
    except CalledProcessError as err:
        api.current_logger().warning(
            'Error during command execution: {}'.format(err)
        )
        return None

    return result['stdout']


def is_mountpoint(mp):
    if not os.path.ismount(mp):
        # Check if mp is actually a mountpoint
        api.current_logger().warning('{} is not mounted'.format(mp))
        return False

    return True


def parse_xfs_info(content):
    """
    This parser reads the output of the ``xfs_info`` command.

    In general the pattern is::

        section =sectionkey key1=value1 key2=value2, key3=value3
                = key4=value4
        nextsec =sectionkey sectionvalue  key=value otherkey=othervalue

    Sections are continued over lines as per RFC822.  The first equals
    sign is column-aligned, and the first key=value is too, but the
    rest seems to be comma separated.  Specifiers come after the first
    equals sign, and sometimes have a value property, but sometimes not.

    NOTE: This function is adapted from [1]

    [1]: https://github.com/RedHatInsights/insights-core/blob/master/insights/parsers/xfs_info.py
    """

    xfs_info = {}

    info_re = re.compile(r'^(?P<section>[\w-]+)?\s*' +
                         r'=(?:(?P<specifier>\S+)(?:\s(?P<specval>\w+))?)?' +
                         r'\s+(?P<keyvaldata>\w.*\w)$'
                         )
    keyval_re = re.compile(r'(?P<key>[\w-]+)=(?P<value>\d+(?: blks)?)')

    sect_info = None

    for line in content:
        match = info_re.search(line)
        if match:
            if match.group('section'):
                # Change of section - make new sect_info dict and link
                sect_info = {}
                xfs_info[match.group('section')] = sect_info
            if match.group('specifier'):
                sect_info['specifier'] = match.group('specifier')
                if match.group('specval'):
                    sect_info['specifier_value'] = match.group('specval')
            for key, value in keyval_re.findall(match.group('keyvaldata')):
                sect_info[key] = value

    _validate_xfs_info(xfs_info)

    return xfs_info


def _validate_xfs_info(xfs_info):
    if 'meta-data' not in xfs_info:
        raise StopActorExecutionError("No 'meta-data' section found")
    if 'specifier' not in xfs_info['meta-data']:
        raise StopActorExecutionError("Device specifier not found in meta-data")
    if 'data' not in xfs_info:
        raise StopActorExecutionError("No 'data' section found")
    if 'blocks' not in xfs_info['data']:
        raise StopActorExecutionError("'blocks' not defined in data section")
    if 'bsize' not in xfs_info['data']:
        raise StopActorExecutionError("'bsize' not defined in data section")
    if 'log' not in xfs_info:
        raise StopActorExecutionError("No 'log' section found")
    if 'blocks' not in xfs_info['log']:
        raise StopActorExecutionError("'blocks' not defined in log section")
    if 'bsize' not in xfs_info['log']:
        raise StopActorExecutionError("'bsize' not defined in log section")


def is_without_ftype(xfs_info):
    return xfs_info['naming'].get('ftype', '') == '0'
