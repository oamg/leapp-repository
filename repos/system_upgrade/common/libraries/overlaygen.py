import contextlib
import os
import shutil
from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting, utils
from leapp.libraries.stdlib import api, CalledProcessError, run

OVERLAY_DO_NOT_MOUNT = ('tmpfs', 'devpts', 'sysfs', 'proc', 'cramfs', 'sysv', 'vfat')


MountPoints = namedtuple('MountPoints', ['fs_file', 'fs_vfstype'])


def _ensure_enough_diskimage_space(space_needed, directory):
    stat = os.statvfs(directory)
    if (stat.f_frsize * stat.f_bavail) < (space_needed * 1024 * 1024):
        message = ('Not enough space available for creating required disk images in {directory}. ' +
                   'Needed: {space_needed} MiB').format(space_needed=space_needed, directory=directory)
        api.current_logger().error(message)
        raise StopActorExecutionError(message)


def _get_mountpoints(storage_info):
    mount_points = set()
    for entry in storage_info.fstab:
        if os.path.isdir(entry.fs_file) and entry.fs_vfstype not in OVERLAY_DO_NOT_MOUNT:
            mount_points.add(MountPoints(entry.fs_file, entry.fs_vfstype))
        elif os.path.isdir(entry.fs_file) and entry.fs_vfstype == 'vfat':
            api.current_logger().warning(
                'Ignoring vfat {} filesystem mount during upgrade process'.format(entry.fs_file)
            )

    return list(mount_points)


def _mount_name(mountpoint):
    return 'root{}'.format(mountpoint.replace('/', '_'))


def _mount_dir(mounts_dir, mountpoint):
    return os.path.join(mounts_dir, _mount_name(mountpoint))


def _prepare_required_mounts(scratch_dir, mounts_dir, mount_points, xfs_info):
    result = {
        mount_point.fs_file: mounting.NullMount(
            _mount_dir(mounts_dir, mount_point.fs_file)) for mount_point in mount_points
    }

    if not xfs_info.mountpoints_without_ftype:
        return result

    space_needed = _overlay_disk_size() * len(xfs_info.mountpoints_without_ftype)
    disk_images_directory = os.path.join(scratch_dir, 'diskimages')

    # Ensure we cleanup old disk images before we check for space contraints.
    run(['rm', '-rf', disk_images_directory])
    _create_diskimages_dir(scratch_dir, disk_images_directory)
    _ensure_enough_diskimage_space(space_needed, scratch_dir)

    mount_names = [mount_point.fs_file for mount_point in mount_points]

    # TODO(pstodulk): this (adding rootfs into the set always) is hotfix for
    # bz #1911802 (not ideal one..). The problem occurs one rootfs is ext4 fs,
    # but /var/lib/leapp/... is under XFS without ftype; In such a case we can
    # see still the very same problems as before. But letting you know that
    # probably this is not the final solution, as we could possibly see the
    # same problems on another partitions too (needs to be tested...). However,
    # it could fit for now until we provide the complete solution around XFS
    # workarounds (including management of required spaces for virtual FSs per
    # mountpoints - without that, we cannot fix this properly)
    for mountpoint in set(xfs_info.mountpoints_without_ftype + ['/']):
        if mountpoint in mount_names:
            image = _create_mount_disk_image(disk_images_directory, mountpoint)
            result[mountpoint] = mounting.LoopMount(source=image, target=_mount_dir(mounts_dir, mountpoint))
    return result


@contextlib.contextmanager
def _build_overlay_mount(root_mount, mounts):
    if not root_mount:
        raise StopActorExecutionError('Root mount point has not been prepared for overlayfs.')
    if not mounts:
        yield root_mount
    else:
        current = list(mounts.keys())[0]
        current_mount = mounts.pop(current)
        name = _mount_name(current)
        with current_mount:
            with mounting.OverlayMount(name=name, source=current, workdir=current_mount.target) as overlay:
                with mounting.BindMount(source=overlay.target,
                                        target=os.path.join(root_mount.target, current.lstrip('/'))):
                    with _build_overlay_mount(root_mount, mounts) as mount:
                        yield mount


def _overlay_disk_size():
    """
    Convenient function to retrieve the overlay disk size
    """
    try:
        env_size = os.getenv('LEAPP_OVL_SIZE', default='2048')
        disk_size = int(env_size)
    except ValueError:
        disk_size = 2048
        api.current_logger().warning(
            'Invalid "LEAPP_OVL_SIZE" environment variable "%s". Setting default "%d" value', env_size, disk_size
        )
    return disk_size


def cleanup_scratch(scratch_dir, mounts_dir):
    """
    Function to cleanup the scratch directory
    """
    api.current_logger().debug('Cleaning up mounts')
    if os.path.ismount(mounts_dir):
        api.current_logger().debug('Mounts directory is a mounted disk image - Unmounting.')
        try:
            run(['/bin/umount', '-fl', mounts_dir])
            api.current_logger().debug('Unmounted mounted disk image.')
        except (OSError, CalledProcessError) as e:
            api.current_logger().warning('Failed to umount %s - message: %s', mounts_dir, str(e))
    api.current_logger().debug('Recursively removing scratch directory %s.', scratch_dir)
    shutil.rmtree(scratch_dir, onerror=utils.report_and_ignore_shutil_rmtree_error)
    api.current_logger().debug('Recursively removed scratch directory %s.', scratch_dir)


def _create_mount_disk_image(disk_images_directory, path):
    """
    Creates the mount disk image, for cases when we hit XFS with ftype=0
    """
    diskimage_path = os.path.join(disk_images_directory, _mount_name(path))
    disk_size = _overlay_disk_size()

    api.current_logger().debug('Attempting to create disk image with size %d MiB at %s', disk_size, diskimage_path)
    utils.call_with_failure_hint(
        cmd=['/bin/dd', 'if=/dev/zero', 'of={}'.format(diskimage_path), 'bs=1M', 'count={}'.format(disk_size)],
        hint='Please ensure that there is enough diskspace in {} at least {} MiB are needed'.format(
            diskimage_path, disk_size)
    )

    api.current_logger().debug('Creating ext4 filesystem in disk image at %s', diskimage_path)
    try:
        utils.call_with_oserror_handled(cmd=['/sbin/mkfs.ext4', '-F', diskimage_path])
    except CalledProcessError as e:
        api.current_logger().error('Failed to create ext4 filesystem %s', exc_info=True)
        raise StopActorExecutionError(
            message=str(e)
        )

    return diskimage_path


def _create_diskimages_dir(scratch_dir, diskimages_dir):
    """
    Prepares directories for disk images
    """
    api.current_logger().debug('Creating disk images directory.')
    try:
        utils.makedirs(diskimages_dir)
        api.current_logger().debug('Done creating disk images directory.')
    except OSError:
        api.current_logger().error('Failed to create disk images directory %s', diskimages_dir, exc_info=True)

        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': 'Please ensure that {scratch_dir} is empty and modifiable.'.format(scratch_dir=scratch_dir)
            }
        )


def _create_mounts_dir(scratch_dir, mounts_dir):
    """
    Prepares directories for mounts
    """
    api.current_logger().debug('Creating mount directories.')
    try:
        utils.makedirs(mounts_dir)
        api.current_logger().debug('Done creating mount directories.')
    except OSError:
        api.current_logger().error('Failed to create mounting directories %s', mounts_dir, exc_info=True)

        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': 'Please ensure that {scratch_dir} is empty and modifiable.'.format(scratch_dir=scratch_dir)
            }
        )


@contextlib.contextmanager
def _mount_dnf_cache(overlay_target):
    """
    Convenience context manager to ensure bind mounted /var/cache/dnf and removal of the mount.
    """
    with mounting.BindMount(
            source='/var/cache/dnf',
            target=os.path.join(overlay_target, 'var', 'cache', 'dnf')) as cache_mount:
        yield cache_mount


@contextlib.contextmanager
def create_source_overlay(mounts_dir, scratch_dir, xfs_info, storage_info, mount_target=None):
    """
    Context manager that prepares the source system overlay and yields the mount.
    """
    api.current_logger().debug('Creating source overlay in {scratch_dir} with mounts in {mounts_dir}'.format(
        scratch_dir=scratch_dir, mounts_dir=mounts_dir))
    try:
        _create_mounts_dir(scratch_dir, mounts_dir)
        mounts = _prepare_required_mounts(scratch_dir, mounts_dir, _get_mountpoints(storage_info), xfs_info)
        with mounts.pop('/') as root_mount:
            with mounting.OverlayMount(name='system_overlay', source='/', workdir=root_mount.target) as root_overlay:
                if mount_target:
                    target = mounting.BindMount(source=root_overlay.target, target=mount_target)
                else:
                    target = mounting.NullMount(target=root_overlay.target)
                with target:
                    with _build_overlay_mount(root_overlay, mounts) as overlay:
                        with _mount_dnf_cache(overlay.target):
                            yield overlay
    except Exception:
        cleanup_scratch(scratch_dir, mounts_dir)
        raise
