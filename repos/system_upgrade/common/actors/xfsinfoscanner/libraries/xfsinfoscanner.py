from leapp.libraries.stdlib import api, run
from leapp.models import StorageInfo, XFSPresence


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


def scan_xfs_systemdmount(data):
    mountpoints = set()
    for entry in data:
        if entry.fs_type == "xfs":
            mountpoints.add(entry.path)

    return mountpoints


def is_xfs_without_ftype(mp):
    for l in run(['/usr/sbin/xfs_info', '{}'.format(mp)], split=True)['stdout']:
        if 'ftype=0' in l:
            return True

    return False


def scan_xfs():
    storage_info_msgs = api.consume(StorageInfo)
    storage_info = next(storage_info_msgs, None)

    if list(storage_info_msgs):
        api.current_logger().warning('Unexpectedly received more than one StorageInfo message.')

    fstab_data = set()
    mount_data = set()
    systemdmount_data = set()
    if storage_info:
        fstab_data = scan_xfs_fstab(storage_info.fstab)
        mount_data = scan_xfs_mount(storage_info.mount)
        systemdmount_data = scan_xfs_systemdmount(storage_info.systemdmount)

    mountpoints = fstab_data | mount_data | systemdmount_data
    mountpoints_ftype0 = list(filter(is_xfs_without_ftype, mountpoints))

    # By now, we only have XFS mountpoints and check whether or not it has ftype = 0
    api.produce(XFSPresence(
        present=len(mountpoints) > 0,
        without_ftype=len(mountpoints_ftype0) > 0,
        mountpoints_without_ftype=mountpoints_ftype0,
    ))
