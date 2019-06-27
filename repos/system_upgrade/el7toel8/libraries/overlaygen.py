import contextlib
import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting, utils
from leapp.libraries.stdlib import CalledProcessError, api, run


def _overlay_disk_size():
    """
    Convenient function to retrieve the overlay disk size
    """
    try:
        env_size = os.getenv('LEAPP_OVL_SIZE', default='2048')
        disk_size = int(env_size)
    except ValueError:
        disk_size = 2048
        api.current_logger().warn(
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
            api.current_logger().warn('Failed to umount %s - message: %s', mounts_dir, e.message)
    api.current_logger().debug('Recursively removing scratch directory %s.', scratch_dir)
    shutil.rmtree(scratch_dir, onerror=utils.report_and_ignore_shutil_rmtree_error)
    api.current_logger().debug('Recursively removed scratch directory %s.', scratch_dir)


@utils.clean_guard(cleanup_function=cleanup_scratch)
def _create_mount_disk_image(scratch_dir, mounts_dir):
    """
    Creates the mount disk image, for cases when we hit XFS with ftype=0
    """
    diskimage_path = os.path.join(scratch_dir, 'diskimage')
    disk_size = _overlay_disk_size()

    api.current_logger().debug('Attempting to create disk image with size %d MiB at %s', disk_size, diskimage_path)
    utils.call_with_failure_hint(
        cmd=['/bin/dd', 'if=/dev/zero', 'of={}'.format(diskimage_path), 'bs=1M', 'count={}'.format(disk_size)],
        hint='Please ensure that there is enough diskspace in {} at least {} MiB are needed'.format(
            scratch_dir, disk_size)
    )

    api.current_logger().debug('Creating ext4 filesystem in disk image at %s', diskimage_path)
    try:
        utils.call_with_oserror_handled(cmd=['/sbin/mkfs.ext4', '-F', diskimage_path])
    except CalledProcessError as e:
        api.current_logger().error('Failed to create ext4 filesystem %s', exc_info=True)
        raise StopActorExecutionError(
            message=e.message
        )

    return diskimage_path


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
def _prepare_mounts(mounts_dir, scratch_dir, cleanup, detach, xfs_present):
    """
    A context manager function that prepares the scratch userspace and creates a mounting target directory. In case of
    XFS with ftype=0 it will trigger the creation of the disk image and mounts it and ensure the cleanup after leaving
    the context.
    """
    if cleanup:
        cleanup_scratch(scratch_dir, mounts_dir)
    _create_mounts_dir(scratch_dir=scratch_dir, mounts_dir=mounts_dir)
    if xfs_present:
        mount = mounting.LoopMount(source=_create_mount_disk_image(scratch_dir, mounts_dir),
                                   target=mounts_dir, config=mounting.MountConfig.MountOnly)
    else:
        mount = mounting.NullMount(target=mounts_dir)
    with mount:
        yield mount


@contextlib.contextmanager
def create_source_overlay(mounts_dir, scratch_dir, xfs_present, cleanup=True, detach=False):
    """
    Context manager that prepares the source system overlay and yields the mount.
    """
    api.current_logger().debug('Creating source overlay in {scratch_dir} with mounts in {mounts_dir}'.format(
        scratch_dir=scratch_dir, mounts_dir=mounts_dir))
    with _prepare_mounts(mounts_dir, scratch_dir, cleanup, detach, xfs_present) as mounts:
        with mounting.OverlayMount(name='source_overlay', source='/', workdir=mounts.target) as overlay:
            with _mount_dnf_cache(overlay.target):
                yield overlay
