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

    if path1 == '' or path2 == '':
        return ''

    path1 = path1.strip('/').split('/')
    path2 = path2.strip('/').split('/')

    common_path = []
    for path1_part, path2_part in zip(path1, path2):
        if path1_part != path2_part:
            break
        common_path.append(path1_part)
    return '/' + '/'.join(common_path)


def _get_incorrectly_ordered_fstab_entries(fstab_entries):
    """
    Retrieve pairs of incorrectly ordered entries in /etc/fstab based on mount point overshadowing.

    :param list[FstabEntry] fstab_entries: fstab entries from StorageInfo
    :returns: pairs of fstab entries with incorrect order
    """

    for i, fstab_entry in enumerate(fstab_entries):
        mount_point = os.path.abspath(fstab_entry.fs_file)

        for overshadowing_fstab_entry in fstab_entries[i+1:]:
            overshadowing_mount_point = os.path.abspath(overshadowing_fstab_entry.fs_file)

            if _get_common_path(mount_point, overshadowing_mount_point) == overshadowing_mount_point:
                yield fstab_entry, overshadowing_fstab_entry


def check_fstab_mount_order():
    storage_info = next(api.consume(StorageInfo), None)

    if storage_info:
        overshadowing_pairs = list(_get_incorrectly_ordered_fstab_entries(storage_info.fstab))
        if overshadowing_pairs:
            mount_points = [fstab_entry.fs_file for fstab_entry in storage_info.fstab]

            duplicates = set()
            overshadowing = set()
            for overshadowed_entry, overshadowing_entry in overshadowing_pairs:
                if overshadowed_entry == overshadowing_entry:
                    duplicates.add(overshadowed_entry.fs_file)
                overshadowing.add(overshadowed_entry.fs_file)
                overshadowing.add(overshadowing_entry.fs_file)

            overshadowing_in_order = []
            for mount_point in mount_points:
                if mount_point in overshadowing:
                    overshadowing_in_order.append(mount_point)

            summary = (
                'Leapp detected incorrect order of entries in /etc/fstab that causes '
                'overshadowing of mount points.\nDetected order of overshadowing mount points:\n{}'
            ).format(', '.join(overshadowing_in_order))

            if duplicates:
                summary += ',\nDetected duplicate mount points:\n{}'.format(', '.join(duplicates))

            hint = (
                'To prevent the overshadowing reorder the entries in /etc/fstab and remove any duplicates. '
                'Possible order of mount points without overshadowing:\n{}'
            ).format(', '.join(sorted(overshadowing, key=len)))

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
