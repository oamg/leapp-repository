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


def _get_overshadowing_mount_points(mount_points):
    """
    Retrieve set of overshadowing and overshadowed mount points.

    :param list[str] mount_points: absolute paths to mount points
    :returns: set of mount points
    """

    overshadowing = set()
    for i, mount_point in enumerate(mount_points):
        if mount_point[-1] == '/':
            mount_point = mount_point[:-1]

        for overshadowing_mount_point in mount_points[i+1:]:
            if overshadowing_mount_point[-1] == '/':
                overshadowing_mount_point = overshadowing_mount_point[:-1]

            if _get_common_path(mount_point, overshadowing_mount_point) == overshadowing_mount_point:
                overshadowing.add(overshadowing_mount_point)
                overshadowing.add(mount_point)

    return overshadowing


def check_fstab_mount_order():
    storage_info = next(api.consume(StorageInfo), None)

    if storage_info:

        mount_points = []
        for fstab_entry in storage_info.fstab:
            mount_point = fstab_entry.fs_file
            if mount_point[-1] == '/':
                mount_point = mount_point[:-1]
            mount_points.append(mount_point)

        overshadowing = _get_overshadowing_mount_points(mount_points)

        if overshadowing:

            overshadowing_in_order = []
            for mount_point in mount_points:
                if mount_point in overshadowing:
                    overshadowing_in_order.append(mount_point)

            duplicates = set()
            for mount_point in mount_points:
                if mount_points.count(mount_point) > 1:
                    duplicates.add(mount_point)

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
