import os

from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import StorageInfo


def _get_common_path(path1, path2):
    """
    Return the longest common absolute sub-path for pair of given absolute paths.

    Note that this function implements similar functionality as os.path.commonpath(), however this function is not
    available in python2.7, thus can't be used here.
    """

    if not path1 or not path2:
        return ''

    path1 = path1.strip('/').split('/')
    path2 = path2.strip('/').split('/')

    common_path = []
    for path1_part, path2_part in zip(path1, path2):
        if path1_part != path2_part:
            break
        common_path.append(path1_part)
    return os.path.join('/', *common_path)


def _get_overshadowing_mount_points(mount_points):
    """
    Retrieve set of overshadowing and overshadowed mount points.

    :param list[str] mount_points: absolute paths to mount points
    :returns: set of unique mount points without trailing /
    """
    overshadowing = set()
    mount_points = [mp.rstrip('/') for mp in mount_points]
    for i, mount_point in enumerate(mount_points):
        for overshadowing_mount_point in mount_points[i+1:]:
            if _get_common_path(mount_point, overshadowing_mount_point) == overshadowing_mount_point:
                overshadowing.add(overshadowing_mount_point)
                overshadowing.add(mount_point)
    return overshadowing


def check_fstab_mount_order():
    storage_info = next(api.consume(StorageInfo), None)

    if not storage_info:
        return

    mount_points = [fstab_entry.fs_file.rstrip('/') for fstab_entry in storage_info.fstab]
    overshadowing = _get_overshadowing_mount_points(mount_points)
    duplicates = {mp for mp in mount_points if mount_points.count(mp) > 1}

    if not overshadowing:
        return

    overshadowing_in_order = [mp for mp in mount_points if mp in overshadowing]
    overshadowing_fixed = sorted(set(mount_points), key=len)
    summary = 'Leapp detected incorrect /etc/fstab format that causes overshadowing of mount points.'
    hint = 'To prevent the overshadowing:'

    if duplicates:
        summary += '\nDetected mount points with duplicates:\n{}'.format(', '.join(duplicates))
        hint += '\nRemove detected duplicates by using unique mount points.'

    if overshadowing:
        summary += '\nDetected order of overshadowing mount points:\n{}'.format(', '.join(overshadowing_in_order))
        hint += (
            '\nReorder the detected overshadowing entries.'
            '\nPossible order of all mount points without overshadowing:\n{}'
        ).format(', '.join(overshadowing_fixed))

    reporting.create_report([
        reporting.Title(
            'Detected incorrect order of entries or duplicate entries in /etc/fstab, preventing a successful '
            'in-place upgrade.'
        ),
        reporting.Summary(summary),
        reporting.Remediation(hint=hint),
        reporting.RelatedResource('file', '/etc/fstab'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])
