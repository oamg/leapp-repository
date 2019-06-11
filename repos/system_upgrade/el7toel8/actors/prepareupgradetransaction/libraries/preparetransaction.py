from collections import namedtuple
import os
import shutil
import sys

from six.moves.urllib.error import URLError
from six.moves.urllib.request import urlopen

from leapp.libraries.stdlib import CalledProcessError, api, run
from leapp.libraries.stdlib.call import STDOUT
from leapp.libraries.stdlib.config import is_debug


OverlayfsInfo = namedtuple('OverlayfsInfo', ['upper', 'work', 'merged'])


class ErrorData(object):
    def __init__(self, details, summary='', spurious=''):
        self.details = details
        self.summary = summary
        self.spurious = spurious

    def __str__(self):
        return '{summary} {details} {spurious}'.format(
            summary=self.summary, details=self.details, spurious=self.spurious)


def connection_guard(url='https://example.com'):
    def closure():
        try:
            urlopen(url)
            return None
        except URLError as e:
            cause = '''Failed to open url '{url}' with error: {error}'''.format(url=url, error=e)
            return ('There was probably a problem with internet conection ({cause}).'
                    ' Check your connection and try again.'.format(cause=cause))
    return closure


def space_guard(path='/', min_free_mb=100):
    def closure():
        info = os.statvfs(path)
        free_mb = (info.f_bavail * info.f_frsize) >> 20
        if free_mb >= min_free_mb:
            return None
        return ('''Not enough free disk space in '{path}', needed: {min} M, available: {avail} M.'''
                ' Free more disk space and try again.'.format(path=path, min=min_free_mb, avail=free_mb))
    return closure


def permission_guard():
    # FIXME: Not implemented yet. Is it even useful?
    raise NotImplementedError


def _logging_handler(fd_info, a_buffer):
    '''Custom log handler to always show DNF stdout to console and stderr only in DEBUG mode'''
    (_unused, fd_type) = fd_info

    if fd_type == STDOUT:
        sys.stdout.write(a_buffer)
    else:
        if is_debug():
            sys.stderr.write(a_buffer)


def guard_call(cmd, guards=(), print_output=False):
    try:
        if print_output:
            return run(cmd, callback_raw=_logging_handler), None
        return run(cmd, split=True)['stdout'], None
    except CalledProcessError as e:
        # return custom error if process failed
        error = ErrorData(details=str(e))

        # collect output from guards for possible spurious failure
        guard_errors = []
        for guard in guards:
            err = guard()
            if err:
                guard_errors.append(err)

        if guard_errors:
            error.spurious = '. Possible spurious failure: {cause}'.format(cause=' '.join(guard_errors))

        return None, error


def guard_container_call(overlayfs_info, cmd, guards=(), print_output=False):
    container_cmd = ['systemd-nspawn', '--register=no', '--quiet', '-D', overlayfs_info.merged]
    return guard_call(container_cmd + cmd, guards=guards, print_output=print_output)


def produce_error(error, summary=None):
    if summary:
        error.summary = summary
    api.report_error(str(error))


def produce_warning(error, summary=None):
    if summary:
        error.summary = summary
    api.current_logger().warn(str(error))


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
                summary='Failed to create Overlayfs directories',
                details=str(e))
            return None, error

    return overlayfs_info, None


def remove_overlayfs_dirs(overlayfs_path):
    shutil.rmtree(overlayfs_path, ignore_errors=True)


def get_list_of_available_repoids(overlayfs_info):
    # TODO: create later library function in this repository that would be
    # + available even for the systemfacts (to get info about orig RHEL
    # + repos)
    cmd = ['subscription-manager', 'repos']
    repoids = []

    repos, error = guard_container_call(overlayfs_info, cmd)
    if error:
        error.summary = 'Failed to get list of available RHEL repositories.'
        return None, error

    for line in repos:
        if line.startswith('Repo ID'):
            repoids.append(line.split(':')[1].strip())
    return set(repoids), None


def mount_overlayfs(overlayfs_info):
    cmd = [
        '/bin/mount',
        '-t',
        'overlay',
        'overlay2',
        '-o',
        'lowerdir=/,upperdir={},workdir={}'.format(overlayfs_info.upper, overlayfs_info.work),
        overlayfs_info.merged
    ]
    _unused, error = guard_call(cmd)
    if error:
        error.summary = 'Error while trying to execute command.'
    return error


def umount_overlayfs(overlayfs_info):
    cmd = [
        '/bin/umount',
        '-fl',
        overlayfs_info.merged
    ]
    _unused, error = guard_call(cmd)
    if error:
        error.summary = 'Error while trying to execute command.'
    return error


def copy_file_to_container(overlayfs_info, orig, dest):
    final_dest = os.path.join(overlayfs_info.merged, dest.lstrip('/'))
    if not os.path.isdir(final_dest):
        try:
            os.makedirs(final_dest)
        except OSError as e:
            return ErrorData(
                summary='Failed to create destination path inside container.',
                details=str(e))

    try:
        shutil.copyfile(orig, os.path.join(final_dest, os.path.basename(orig)))
    except IOError as e:
        return ErrorData(
            summary='Failed to copy file to container.',
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


def mount_dnf_cache(overlayfs_info):
    overlayfs_dnf_cache = os.path.join(overlayfs_info.merged, 'var', 'cache', 'dnf')
    # FIXME: fails on insufficient permissions
    cmds = [
        ['/bin/rm', '-rf', overlayfs_dnf_cache],
        ['/bin/mkdir', '-p', overlayfs_dnf_cache],
        ['/bin/mount', '--bind', '/var/cache/dnf', overlayfs_dnf_cache]]

    for cmd in cmds:
        _unused, error = guard_call(cmd)
        if error:
            error.summary = 'Failed to mount dnf cache.'
            return error
    return None


def umount_dnf_cache(overlayfs_info):
    _unused, error = guard_call(['/bin/umount', os.path.join(overlayfs_info.merged, 'var', 'cache', 'dnf')])
    if error:
        error.summary = 'Failed to unmount dnf cache.'
    return error


def create_disk_image(path):
    diskimage_path = os.path.join(path, 'diskimage')
    mounts_path = os.path.join(path, 'mounts')

    if os.path.isdir(mounts_path):
        remove_disk_image(path)

    try:
        os.makedirs(mounts_path)
    except OSError as e:
        return ErrorData(
            summary='Error while trying to create destination path on the host system.',
            details=str(e))

    disk_size = os.getenv('LEAPP_OVL_SIZE', default='2048')

    try:
        int(disk_size)
    except ValueError:
        disk_size = '2048'
        api.current_logger().warn(
            'Invalid "LEAPP_OVL_SIZE" environment variable. Setting default "{}" value'.format(disk_size))

    cmds = [['/bin/dd', 'if=/dev/zero', 'of={}'.format(diskimage_path), 'bs=1M', 'count={}'.format(disk_size)],
            ['/sbin/mkfs.ext4', '-F', diskimage_path],
            ['/bin/mount', '-o', 'loop', diskimage_path, mounts_path]]

    for cmd in cmds:
        _unused, err = guard_call(cmd)
        if err:
            return err
    return None


def remove_disk_image(path):
    if os.path.ismount(os.path.join(path, 'mounts')):
        guard_call(['/bin/umount', '-fl', os.path.join(path, 'mounts')])
    shutil.rmtree(path, ignore_errors=True)
