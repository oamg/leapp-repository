import os
import shutil
import six
import subprocess
from collections import namedtuple


ErrorData = namedtuple('ErrorData', ['summary', 'details'])
OverlayfsInfo = namedtuple('OverlayfsInfo', ['upper', 'work', 'merged'])


def create_overlayfs_dirs(overlayfs_path):

    overlayfs_info = OverlayfsInfo(
        upper=os.path.join(overlayfs_path, 'upper'),
        work=os.path.join(overlayfs_path, 'work'),
        merged=os.path.join(overlayfs_path, 'merged'))

    if os.path.isdir(overlayfs_path):
        # Ignoring any error when trying to umount preexisting Overlayfs
        # FIXME: handle errors caused by umount
        umount_overlayfs(overlayfs_info)
        remove_overlayfs_dirs(overlayfs_path)

    for d in overlayfs_info:
        try:
            os.makedirs(d)
        except OSError as e:
            error = ErrorData(
                summary='Error while trying to create Overlayfs directories',
                details=str(e))
            return None, error

    return overlayfs_info, None


def remove_overlayfs_dirs(overlayfs_path):
    shutil.rmtree(overlayfs_path, ignore_errors=True)


def get_list_of_available_repo_uids(overlayfs_info):
    # TODO: create later library function in this repository that would be
    # + available even for the systemfacts (to get info about orig RHEL
    # + repos)
    cmd = ['subscription-manager', 'repos', ]
    uids = []
    for line in container_call(overlayfs_info, cmd, split=True):
        if line.startswith('Repo ID'):
            uids.append(line.split(':')[1].strip())
    return uids


def container_call(overlayfs_info, cmd, split):
    container_cmd = ['systemd-nspawn', '--register=no', '-D', overlayfs_info.merged]
    return call(container_cmd + cmd, split)


# NOTE: The function is used in several actors, should be moved to the library
# NOTE: It really ugly to have something like this here, I know...
def call(args, split=True):
    ''' Call external processes with some additional sugar '''
    r = None
    with open(os.devnull, mode='w') as err:
        if six.PY3:
            r = subprocess.check_output(args, stderr=err, encoding='utf-8')
        else:
            r = subprocess.check_output(args, stderr=err).decode('utf-8')
    if split:
        return r.splitlines()
    return r


def check_cmd_call(cmd):
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        return ErrorData(
            summary='Error while trying to execute command',
            details=str(e))
    return None


def mount_overlayfs(overlayfs_info):
    return check_cmd_call([
        '/bin/mount',
        '-t',
        'overlay',
        'overlay2',
        '-o',
        'lowerdir=/,upperdir={},workdir={}'.format(overlayfs_info.upper, overlayfs_info.work),
        overlayfs_info.merged])


def umount_overlayfs(overlayfs_info):
    return check_cmd_call([
        '/bin/umount',
        '-fl',
        overlayfs_info.merged])


def copy_file_to_container(overlayfs_info, orig, dest):
    final_dest = os.path.join(overlayfs_info.merged, dest.lstrip('/'))
    if not os.path.isdir(final_dest):
        try:
            os.makedirs(final_dest)
        except OSError as e:
            return ErrorData(
                summary='Error while trying to create destination path inside container',
                details=str(e))

    try:
        shutil.copyfile(orig, os.path.join(final_dest, os.path.basename(orig)))
    except IOError as e:
        return ErrorData(
            summary='Error while trying to copy file to container',
            details=str(e))

    return None


# FIXME: both copy_* functions should check whether dest isdir or basename
# + is already wanted filename
def copy_file_from_container(overlayfs_info, orig, dest, filename=None):
    orig_src = os.path.join(overlayfs_info.merged, orig.lstrip('/'))
    if not os.path.isdir(dest):
        try:
            os.makedirs(dest)
        except OSError as e:
            return ErrorData(
                summary='Error while trying to create destination path on the host system.',
                details=str(e))

    try:
        if not filename:
            filename = os.path.basename(orig)
        shutil.copyfile(orig_src, os.path.join(dest, filename))
    except IOError as e:
        return ErrorData(
            summary='Error while trying to copy file from container',
            details=str(e))

    return None


def check_container_call(overlayfs_info, cmd):
    container_cmd = ['systemd-nspawn', '--register=no', '-D', overlayfs_info.merged]
    return check_cmd_call(container_cmd + cmd)


def mount_dnf_cache(overlayfs_info):
    overlayfs_dnf_cache = os.path.join(overlayfs_info.merged, 'var', 'cache', 'dnf')
    cmds = [
        ['/bin/rm', '-rf', overlayfs_dnf_cache],
        ['/bin/mkdir', '-p', overlayfs_dnf_cache],
        ['/bin/mount', '--bind', '/var/cache/dnf', overlayfs_dnf_cache]]

    for cmd in cmds:
        error = check_cmd_call(cmd)
        if error:
            return error
    return None


def umount_dnf_cache(overlayfs_info):
    return check_cmd_call(['/bin/umount', os.path.join(overlayfs_info.merged, 'var', 'cache', 'dnf')])
