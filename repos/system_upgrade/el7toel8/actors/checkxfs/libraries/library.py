from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, call
from leapp.models import StorageInfo, XFSPresence


def check_xfs_fstab(data):
    mountpoints = set()
    for entry in data:
        if entry.fs_vfstype == "xfs":
            mountpoints.add(entry.fs_file)

    return mountpoints


def check_xfs_mount(data):
    mountpoints = set()
    for entry in data:
        if entry.tp == "xfs":
            mountpoints.add(entry.mount)

    return mountpoints


def check_xfs_systemdmount(data):
    mountpoints = set()
    for entry in data:
        if entry.fs_type == "xfs":
            mountpoints.add(entry.path)

    return mountpoints


def is_xfs_without_ftype(mp):
    for l in call(['/usr/sbin/xfs_info', '{}'.format(mp)]):
        if 'ftype=0' in l:
            return True
    
    return False

   
def check_xfs():
    storage_info_msgs = api.consume(StorageInfo)
    storage_info = next(storage_info_msgs, None)

    if list(storage_info_msgs):
        api.current_logger().warning('Unexpectedly received more than one StorageInfo message.')
    if not storage_info:
        raise StopActorExecutionError('Could not check if XFS is in use.',
                                      details={'details': 'Did not receive a StorageInfo message'})


    fstab_data = check_xfs_fstab(storage_info.fstab)
    mount_data = check_xfs_mount(storage_info.mount)
    systemdmount_data = check_xfs_systemdmount(storage_info.systemdmount)

    mountpoints = fstab_data | mount_data | systemdmount_data
    
    xfs_presence = XFSPresence()
    # By now, we only care for XFS without ftype in use for /var
    for mp in ('/var', '/'):
        if mp in mountpoints:
            xfs_presence.present = True
            xfs_presence.without_ftype = is_xfs_without_ftype(mp)
            break

    api.produce(xfs_presence)
