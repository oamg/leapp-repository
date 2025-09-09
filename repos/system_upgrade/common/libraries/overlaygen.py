import contextlib
import os
import shutil
import sys
from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting, utils
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api, CalledProcessError, run

OVERLAY_DO_NOT_MOUNT = ('tmpfs', 'devtmpfs', 'devpts', 'sysfs', 'proc', 'cramfs', 'sysv', 'vfat')

# NOTE(pstodulk): what about using more closer values and than just multiply
# the final result by magical constant?... this number is most likely going to
# be lowered and affected by XFS vs EXT4 FSs that needs different spaces each
# of them.
_MAGICAL_CONSTANT_OVL_SIZE = 128
"""
Average size of created disk space images.

The size can be lower or higher - usually lower. The value is higher as we want
to rather prevent future actions in advance instead of resolving later issues
with the missing space.

It's possible that in future we implement better heuristic that will guess
the needed space based on size of each FS. I have been thinking to lower
the value, as in my case most of partitions where we do not need to do
write operations consume just ~ 33MB. However, I decided to keep it as it is
for now to stay on the safe side.
"""

_MAGICAL_CONSTANT_MIN_CONTAINER_SIZE = 2200
"""
Average space consumed to create target userspace container installation + pkg downloads.

Minimal container size is approx. 1GiB without download of packages for the upgrade
(and without pkgs for the initramfs creation). The total size of the container
  * with all pkgs downloaded
  * final initramfs installed package set
  * created the upgrade initramfs
is for the minimal system
  * ~ 1.8 GiB for IPU 8 -> 9 and IPU 9 -> 10
when no other extra packages are installed for the needs of the upgrade.
Keeping in mind that during the upgrade another 400+ MiB is consumed
temporarily during initramfs creation.

Using higher value to cover also the space that consumes leapp.db records.

This constant is really magical and the value can be changed in future.
"""

_MAGICAL_CONSTANT_MIN_PROTECTED_SIZE = 200
"""
This is the minimal size (in MiB) that will be always reserved for /var/lib/leapp

In case the size of the container is larger than _MAGICAL_CONSTANT_MIN_PROTECTED_SIZE
or close to that size, stay always with this minimal protected size defined by
this constant.
"""

_MAX_DISK_IMAGE_SIZE_MB = 2**20  # 1*TB
"""
Maximum size of the created (sparse) images.

Defaults to 1TB. If a disk with capacity larger than _MAX_DISK_IMAGE_SIZE_MB
is mounted on the system, the corresponding image used to store overlay
modifications will be capped to _MAX_DISK_IMAGE_SIZE_MB.

Engineering rationale:
   This constant was introduced to prevent leapp from creating files that are
   virtually larger than the maximum file size supported by the file system.
   E.g. if the source system hosts /var/lib/leapp on EXT4, then we cannot
   create a file larger than 16TB.
   We create these "disk images" to be able to verify the system has enough
   disk space to perform the RPM upgrade transaction. From our experience,
   we are not aware of any system which could have installed so much content
   by RPMs that we would need 1TB of the free space on a single FS. Therefore,
   we consider this value as safe while preventing us from exceeding FS
   limits.
"""


MountPoints = namedtuple('MountPoints', ['fs_file', 'fs_vfstype'])


def _get_min_container_size():
    return _MAGICAL_CONSTANT_MIN_CONTAINER_SIZE


def get_recommended_leapp_free_space(userspace_path=None):
    """
    Return recommended free space for the target container (+ pkg downloads)

    If the path to the container is set, the returned value is updated to
    reflect already consumed space by the installed container. In case the
    container is bigger than the minimal protected size, return at least
    `_MAGICAL_CONSTANT_MIN_PROTECTED_SIZE`.

    It's not recommended to use this function except official actors managed
    by OAMG group in github.com/oamg/leapp-repository. This function can be
    changed in future, ignoring the deprecation process.

    TODO(pstodulk): this is so far the best trade off between stay safe and do
    do not consume too much space. But need to figure out cost of the time
    consumption.

    TODO(pstodulk): check we are not negatively affected in case of downloaded
    rpms. We want to prevent situations when we say that customer has enough
    space for the first run and after the download of packages we inform them
    they do not have enough free space anymore. Note: such situation can be
    valid in specific cases - e.g. the space is really consumed already e.g. by
    leapp.db that has been executed manytimes.

    :param userspace_path: Path to the userspace container.
    :type userspace_path: str
    :rtype: int
    """
    min_cont_size = _get_min_container_size()
    if not userspace_path or not os.path.exists(userspace_path):
        return min_cont_size
    try:
        # ignore symlinks and other partitions to be sure we calculate the space
        # in reasonable time
        cont_size = run(['du', '-sPmx', userspace_path])['stdout'].split()[0]
        # the obtained number is in KiB. But we want to work with MiBs rather.
        cont_size = int(cont_size)
    except (OSError, CalledProcessError):
        # do not care about failed cmd, in such a case, just act like userspace_path
        # has not been set
        api.current_logger().warning(
            'Cannot calculate current container size to estimate correctly required space.'
            ' Working with the default: {} MiB'
            .format(min_cont_size)
        )
        return min_cont_size
    if cont_size < 0:
        api.current_logger().warning(
            'Cannot calculate the container size - negative size obtained: {}.'
            ' Estimate the required size based on the default value: {} MiB'
            .format(cont_size, min_cont_size)
        )
        return min_cont_size
    prot_size = min_cont_size - cont_size
    if prot_size < _MAGICAL_CONSTANT_MIN_PROTECTED_SIZE:
        api.current_logger().debug(
            'The size of the container is higher than the expected default.'
            ' Use the minimal protected size instead: {} MiB.'
            .format(_MAGICAL_CONSTANT_MIN_PROTECTED_SIZE)
        )
        return _MAGICAL_CONSTANT_MIN_PROTECTED_SIZE
    return prot_size


def _get_fspace(path, convert_to_mibs=False, coefficient=1.0):
    """
    Return the free disk space on given path.

    The default is in bytes, but if convert_to_mibs is True, return MiBs instead.

    Raises OSError if nothing exists on the given `path`.

    :param path: Path to an existing file or directory
    :type path: str
    :param convert_to_mibs: If True, convert the value to MiBs
    :type convert_to_mibs: bool
    :param coefficient: Coefficient to multiply the free space (e.g. 0.9 to have it 10% lower). Max: 1
    :type coefficient: float
    :rtype: int
    """
    stat = os.statvfs(path)

    # TODO(pstodulk): discuss the function params
    coefficient = min(coefficient, 1)
    fspace_bytes = int(stat.f_frsize * stat.f_bavail * coefficient)
    if convert_to_mibs:
        return int(fspace_bytes / 1024 / 1024)  # noqa: W1619; pylint: disable=old-division
    return fspace_bytes


def _ensure_enough_diskimage_space(space_needed, directory):
    # TODO(pstodulk): update the error msg/details
    # imagine situation we inform user we need at least 800MB,
    # so they clean /var/lib/leapp/* which can provide additional space,
    # but the calculated required free space takes the existing content under
    # /var/lib/leapp/ into account, so the next error msg could say:
    #    needed at least 3400 MiB - which could be confusing for users.
    if _get_fspace(directory) < (space_needed * 1024 * 1024):
        message = (
            'Not enough space available on {directory}: Needed at least {space_needed} MiB.'
            .format(directory=directory, space_needed=space_needed)
        )
        details = {'detail': (
            'The file system hosting the {directory} directory does not contain'
            ' enough free space to proceed all parts of the in-place upgrade.'
            ' Note the calculated required free space is the minimum derived'
            ' from upgrades of minimal systems and the actual needed free'
            ' space could be higher.'
            '\nNeeded at least: {space_needed} MiB.'
            '\nSuggested free space: {suggested} MiB (or more).'
            .format(space_needed=space_needed, directory=directory, suggested=space_needed + 1000)
        )}
        if get_env('LEAPP_OVL_SIZE', None):
            # LEAPP_OVL_SIZE has not effect as we use sparse files now.
            details['note'] = 'The LEAPP_OVL_SIZE environment variable has no effect anymore.'
        api.current_logger().error(message)
        raise StopActorExecutionError(message, details=details)


def _get_mountpoints(storage_info):
    mount_points = set()
    for entry in storage_info.fstab:
        if os.path.isdir(entry.fs_file) and entry.fs_vfstype not in OVERLAY_DO_NOT_MOUNT:
            mount_points.add(MountPoints(entry.fs_file, entry.fs_vfstype))
        elif os.path.isdir(entry.fs_file) and entry.fs_vfstype == 'vfat':
            # VFAT FS is not supported to be used for any system partition,
            # so we can safely ignore it
            api.current_logger().warning(
                'Ignoring vfat {} filesystem mount during upgrade process'.format(entry.fs_file)
            )

    return list(mount_points)


def _mount_name(mountpoint):
    return 'root{}'.format(mountpoint.replace('/', '_'))


def _mount_dir(mounts_dir, mountpoint):
    return os.path.join(mounts_dir, _mount_name(mountpoint))


def _get_scratch_mountpoint(mount_points, dir_path):
    for mp in sorted(mount_points, reverse=True):
        # we are sure that mountpoint != dir_path in this case, as the latest
        # valid mountpoint customers could create is the parent directory
        mod_mp = mp if mp[-1] == '/' else '{}/'.format(mp)
        if dir_path.startswith(mod_mp):
            # longest first, so the first one we find, is the last mp on the path
            return mp
    return None  # making pylint happy; this is basically dead code


def _prepare_required_mounts(scratch_dir, mounts_dir, storage_info, scratch_reserve):
    """
    Create disk images and loop mount them.

    Ensure to create disk image for each important mountpoint configured
    in fstab (excluding fs types noted in `OVERLAY_DO_NOT_MOUNT`).
    Disk images reflect the free space of related partition/volume. In case
    of partition hosting /var/lib/leapp/* calculate the free space value
    taking `scratch_reserve` into account, as during the run of the tooling,
    we will be consuming the space on the partition and we want to be more
    sure that we do not consume all the space on the partition during the
    execution - so we reduce the risk we affect run of other applications
    due to missing space.

    Note: the partition hosting the scratch dir is expected to be the same
    partition that is hosting the target userspace container, but it does not
    have to be true if the code changes. Right now, let's live with that.

    See `_create_mount_disk_image` docstring for additional more details.

    :param scratch_dir: Path to the scratch directory.
    :type scratch_dir: str
    :param mounts_dir: Path to the directory supposed to be a mountpoint.
    :type mounts_dir: str
    :param storage_info: The StorageInfo message.
    :type storage_info: leapp.models.StorageInfo
    :param scratch_reserve: Number of MB that should be extra reserved in a partition hosting the scratch_dir.
    :type scratch_reserve: Optional[int]
    """
    mount_points = sorted([mp.fs_file for mp in _get_mountpoints(storage_info)])
    scratch_mp = _get_scratch_mountpoint(mount_points, scratch_dir)
    disk_images_directory = os.path.join(scratch_dir, 'diskimages')

    # Ensure we cleanup old disk images before we check for space constraints.
    # NOTE(pstodulk): Could we improve the process so we create imgs & calculate
    # the required disk space just once during each leapp (pre)upgrade run?
    run(['rm', '-rf', disk_images_directory])
    _create_diskimages_dir(scratch_dir, disk_images_directory)

    # TODO(pstodulk): update the calculation for bind mounted mount_points (skip)
    # basic check whether we have enough space at all
    space_needed = scratch_reserve + _MAGICAL_CONSTANT_OVL_SIZE * len(mount_points)
    _ensure_enough_diskimage_space(space_needed, scratch_dir)

    # free space required on this partition should not be affected by during the
    # upgrade transaction execution by space consumed on creation of disk images
    # as disk images are cleaned in the end of this functions,
    # but we want to reserve some space in advance.
    scratch_disk_size = _get_fspace(scratch_dir, convert_to_mibs=True) - scratch_reserve

    result = {}
    for mountpoint in mount_points:
        # keep the info about the free space rather 5% lower than the real value
        disk_size = _get_fspace(mountpoint, convert_to_mibs=True, coefficient=0.95)
        if mountpoint == scratch_mp:
            disk_size = scratch_disk_size

        if disk_size > _MAX_DISK_IMAGE_SIZE_MB:
            msg = ('Image for overlayfs corresponding to the disk mounted at %s would ideally have %d MB, '
                   'but we truncate it to %d MB to avoid bumping to max file limits.')
            api.current_logger().info(msg, mountpoint, disk_size, _MAX_DISK_IMAGE_SIZE_MB)
            disk_size = _MAX_DISK_IMAGE_SIZE_MB

        image = _create_mount_disk_image(disk_images_directory, mountpoint, disk_size)
        result[mountpoint] = mounting.LoopMount(
            source=image,
            target=_mount_dir(mounts_dir, mountpoint)
        )
    return result


@contextlib.contextmanager
def _build_overlay_mount(root_mount, mounts):
    # noqa: W0135; pylint: disable=contextmanager-generator-missing-cleanup
    # NOTE(pstodulk): the pylint check is not valid in this case - finally is covered
    # implicitly
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


def cleanup_scratch(scratch_dir, mounts_dir):
    """
    Function to cleanup the scratch directory

    If the mounts_dir is a mountpoint, unmount it first.

    :param scratch_dir: Path to the scratch directory.
    :type scratch_dir: str
    :param mounts_dir: Path to the directory supposed to be a mountpoint.
    :type mounts_dir: str
    """
    api.current_logger().debug('Cleaning up mounts')
    if os.path.ismount(mounts_dir):
        # TODO(pstodulk): this is actually obsoleted for years. mounts dir
        # is not mountpoit anymore, it contains mountpoints. But in time of
        # this call all MPs should be already umounted as the solution has been
        # changed also (all MPs are handled by context managers). This code
        # is basically dead, so keeping it as it does not hurt us now.
        api.current_logger().debug('Mounts directory is a mounted disk image - Unmounting.')
        try:
            run(['/bin/umount', '-fl', mounts_dir])
            api.current_logger().debug('Unmounted mounted disk image.')
        except (OSError, CalledProcessError) as e:
            api.current_logger().warning('Failed to umount %s - message: %s', mounts_dir, str(e))
    if get_env('LEAPP_DEVEL_KEEP_DISK_IMGS', None) == '1':
        # NOTE(pstodulk): From time to time, it helps me with some experiments
        return
    api.current_logger().debug('Recursively removing scratch directory %s.', scratch_dir)
    if sys.version_info >= (3, 12):
        # NOTE(mmatuska): The pylint suppressions are required because of a bug in pylint:
        # (https://github.com/pylint-dev/pylint/issues/9622)
        shutil.rmtree(scratch_dir, onexc=utils.report_and_ignore_shutil_rmtree_error)  # noqa: E501; pylint: disable=unexpected-keyword-arg
    else:
        shutil.rmtree(scratch_dir, onerror=utils.report_and_ignore_shutil_rmtree_error)  # noqa: E501; pylint: disable=deprecated-argument
    api.current_logger().debug('Recursively removed scratch directory %s.', scratch_dir)


def _format_disk_image_ext4(diskimage_path):
    """
    Format the specified disk image with Ext4 filesystem.

    The formatted file system is optimized for operations we want to do and
    mainly for the space it needs to take for the initialisation. So use 32MiB
    journal (that's enough for us as we do not plan to do too many operations
    inside) for any size of the disk image. Also the lazy
    initialisation is disabled. The formatting will be slower, but it helps
    us to estimate better the needed amount of the space for other actions
    done later.
    """
    api.current_logger().debug('Creating ext4 filesystem in disk image at %s', diskimage_path)
    cmd = [
        '/sbin/mkfs.ext4',
        '-J', 'size=32',
        '-E', 'lazy_itable_init=0,lazy_journal_init=0',
        '-F', diskimage_path
    ]
    try:
        utils.call_with_oserror_handled(cmd=cmd)
    except CalledProcessError as e:
        # FIXME(pstodulk): taken from original, but %s seems to me invalid here
        api.current_logger().error('Failed to create ext4 filesystem in %s', diskimage_path, exc_info=True)
        raise StopActorExecutionError(
            message='Cannot create Ext4 filesystem in {}'.format(diskimage_path),
            details={
                'error message': str(e),
            }
        )


def _format_disk_image_xfs(diskimage_path):
    """
    Format the specified disk image with XFS filesystem.

    Set journal just to 32MiB always as we will not need to do too many operation
    inside, so 32MiB should enough for us.
    """
    api.current_logger().debug('Creating XFS filesystem in disk image at %s', diskimage_path)
    cmd = ['/sbin/mkfs.xfs', '-l', 'size=32m', '-f', diskimage_path]
    try:
        utils.call_with_oserror_handled(cmd=cmd)
    except CalledProcessError as e:
        # FIXME(pstodulk): taken from original, but %s seems to me invalid here
        api.current_logger().error('Failed to create XFS filesystem %s', diskimage_path, exc_info=True)
        raise StopActorExecutionError(
            message='Cannot create XFS filesystem in {}'.format(diskimage_path),
            details={
                'error message': str(e),
            }
        )


def _create_mount_disk_image(disk_images_directory, path, disk_size):
    """
    Creates the mount disk image and return path to it.

    The disk image is represented by a sparse file which apparent size
    corresponds usually to the free space of a particular partition/volume it
    represents - in this function it's set by `disk_size` parameter, which should
    be int representing the free space in MiBs.

    The created disk image is formatted with XFS (default) or Ext4 FS
    and it's supposed to be used for write directories of an overlayfs built
    above it.

    If the disk_size is lower than 130 MiBs, the disk size is automatically
    set to 130 MiBs to be able to format it correctly.

    The disk image is formatted with Ext4 if (envar) `LEAPP_OVL_IMG_FS_EXT4=1`.

    :param disk_images_directory: Path to the directory where disk images should be stored.
    :type disk_images_directory: str
    :param path: Path to the mountpoint of the original (host/source) partition/volume
    :type path: str
    :param disk_size: Apparent size of the disk img in MiBs
    :type disk_size: int
    :return: Path to the created disk image
    :rtype: str
    """
    if disk_size < 130:
        # NOTE(pstodulk): SEATBELT
        # min. required size for current params to format a disk img with a FS:
        #   XFS  -> 130 MiB
        #   EXT4 -> 70  MiB
        # so let's stick to 130 always. This is expected to happen when:
        #  * the free space on a system mountpoint is really super small, but if
        #    such a mounpoint contains a content installed by packages, most
        #    likely the msg about not enough free space is raised
        #  * the mountpoint is actually no important at all, could be possibly
        #    read only (e.g. ISO), or it's an FS type that should be covered by
        #    OVERLAY_DO_NOT_MOUNT
        #  * most common case important for us here could be /boot, but that's
        #    covered already in different actors/checks, so it should not be
        #    problem either
        # NOTE(pstodulk): In case the formatting params are modified,
        # the minimal required size could be different
        api.current_logger().warning(
            'The apparent size for the disk image representing {path}'
            ' is too small ({disk_size} MiBs) for a formatting. Setting 130 MiBs instead.'
            .format(path=path, disk_size=disk_size)
        )
        disk_size = 130
    diskimage_path = os.path.join(disk_images_directory, _mount_name(path))
    cmd = [
        '/bin/dd',
        'if=/dev/zero', 'of={}'.format(diskimage_path),
        'bs=1M', 'count=0', 'seek={}'.format(disk_size)
    ]
    hint = (
        'Please ensure that there is enough diskspace on the partition hosting'
        'the {} directory.'
        .format(disk_images_directory)
    )

    api.current_logger().debug('Attempting to create disk image at %s', diskimage_path)
    utils.call_with_failure_hint(cmd=cmd, hint=hint)

    if get_env('LEAPP_OVL_IMG_FS_EXT4', '0') == '1':
        # This is alternative to XFS in case we find some issues, to be able
        # to switch simply to Ext4, so we will be able to simple investigate
        # possible issues between overlay <-> XFS if any happens.
        _format_disk_image_ext4(diskimage_path)
    else:
        _format_disk_image_xfs(diskimage_path)

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
    # noqa: W0135; pylint: disable=contextmanager-generator-missing-cleanup
    # NOTE(pstodulk): the pylint check is not valid in this case - finally is covered
    # implicitly
    with mounting.BindMount(
            source='/var/cache/dnf',
            target=os.path.join(overlay_target, 'var', 'cache', 'dnf')) as cache_mount:
        yield cache_mount


@contextlib.contextmanager
def create_source_overlay(mounts_dir, scratch_dir, xfs_info, storage_info, mount_target=None, scratch_reserve=0):
    """
    Context manager that prepares the source system overlay and yields the mount.

    The in-place upgrade itself requires to do some changes on the system to be
    able to perform the in-place upgrade itself - or even to be able to evaluate
    if the system is possible to upgrade. However, we do not want to (and must not)
    change the original system until we pass beyond the point of not return.

    For that purposes we have to create a layer above the real host file system,
    where we can safely perform all operations without affecting the system
    setup, rpm database, etc. Currently overlay (OVL) technology showed it is
    capable to handle our requirements good enough - with some limitations.

    This function prepares a disk image and an overlay layer for each
    mountpoint configured in /etc/fstab, excluding those with FS type noted
    in the OVERLAY_DO_NOT_MOUNT set. Such prepared OVL images are then composed
    together to reflect the real host filesystem. In the end everything is cleaned.

    The new solution can be now problematic for system with too many partitions
    and loop devices. For such systems we keep for now the possibility of the
    fallback to an old solution, which has however number of issues that are
    fixed by the new design. To fallback to the old solution, set envar:
        LEAPP_OVL_LEGACY=1

    Disk images created for OVL are formatted with XFS by default. In case of
    problems, it's possible to switch to Ext4 FS using:
        LEAPP_OVL_IMG_FS_EXT4=1

    :param mounts_dir: Absolute path to the directory under which all mounts should happen.
    :type mounts_dir: str
    :param scratch_dir: Absolute path to the directory in which all disk and OVL images are stored.
    :type scratch_dir: str
    :param xfs_info: The XFSPresence message.
    :type xfs_info: leapp.models.XFSPresence
    :param storage_info: The StorageInfo message.
    :type storage_info: leapp.models.StorageInfo
    :param mount_target: Directory to which whole source OVL layer should be bind mounted.
                         If None (default), mounting.NullMount is created instead
    :type mount_target: Optional[str]
    :param scratch_reserve: Number of MB that should be extra reserved in a partition hosting the scratch_dir.
    :type scratch_reserve: Optional[int]
    :rtype: mounting.BindMount or mounting.NullMount
    """
    # noqa: W0135; pylint: disable=contextmanager-generator-missing-cleanup
    # NOTE(pstodulk): the pylint check is not valid in this case - finally is covered
    # implicitly
    api.current_logger().debug('Creating source overlay in {scratch_dir} with mounts in {mounts_dir}'.format(
        scratch_dir=scratch_dir, mounts_dir=mounts_dir))
    try:
        _create_mounts_dir(scratch_dir, mounts_dir)
        if get_env('LEAPP_OVL_LEGACY', '0') != '1':
            mounts = _prepare_required_mounts(scratch_dir, mounts_dir, storage_info, scratch_reserve)
        else:
            # fallback to the deprecated OVL solution
            mounts = _prepare_required_mounts_old(scratch_dir, mounts_dir, _get_mountpoints(storage_info), xfs_info)
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
    finally:
        cleanup_scratch(scratch_dir, mounts_dir)


# #############################################################################
# Deprecated OVL solution ...
# This is going to be removed in future as the whole functionality is going to
# be replaced by new one. The problem is that the new solution can potentially
# negatively affect systems with many loop mountpoints, so let's keep this
# as a workaround for now. I am separating the old and new code in this way
# to make the future removal easy.
# The code below is triggered when LEAPP_OVL_LEGACY=1 envar is set.
# IMPORTANT: Before an update of functions above, ensure the functionality of
# the code below is not affected, otherwise copy the function below with the
# "_old" suffix.
# #############################################################################
def _ensure_enough_diskimage_space_old(space_needed, directory):
    stat = os.statvfs(directory)
    if (stat.f_frsize * stat.f_bavail) < (space_needed * 1024 * 1024):
        message = ('Not enough space available for creating required disk images in {directory}. ' +
                   'Needed: {space_needed} MiB').format(space_needed=space_needed, directory=directory)
        api.current_logger().error(message)
        raise StopActorExecutionError(message)


def _overlay_disk_size_old():
    """
    Convenient function to retrieve the overlay disk size
    """
    env_size = get_env('LEAPP_OVL_SIZE', '2048')
    try:
        disk_size = int(env_size)
    except ValueError:
        disk_size = 2048
        api.current_logger().warning(
            'Invalid "LEAPP_OVL_SIZE" environment variable "%s". Setting default "%d" value', env_size, disk_size
        )
    return disk_size


def _create_diskimages_dir_old(scratch_dir, diskimages_dir):
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


def _create_mount_disk_image_old(disk_images_directory, path):
    """
    Creates the mount disk image, for cases when we hit XFS with ftype=0
    """
    diskimage_path = os.path.join(disk_images_directory, _mount_name(path))
    disk_size = _overlay_disk_size_old()

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
        api.current_logger().error('Failed to create ext4 filesystem in %s', exc_info=True)
        raise StopActorExecutionError(
            message=str(e)
        )

    return diskimage_path


def _prepare_required_mounts_old(scratch_dir, mounts_dir, mount_points, xfs_info):
    result = {
        mount_point.fs_file: mounting.NullMount(
            _mount_dir(mounts_dir, mount_point.fs_file)) for mount_point in mount_points
    }

    if not xfs_info.mountpoints_without_ftype:
        return result

    space_needed = _overlay_disk_size_old() * len(xfs_info.mountpoints_without_ftype)
    disk_images_directory = os.path.join(scratch_dir, 'diskimages')

    # Ensure we cleanup old disk images before we check for space constraints.
    run(['rm', '-rf', disk_images_directory])
    _create_diskimages_dir_old(scratch_dir, disk_images_directory)
    _ensure_enough_diskimage_space_old(space_needed, scratch_dir)

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
            image = _create_mount_disk_image_old(disk_images_directory, mountpoint)
            result[mountpoint] = mounting.LoopMount(source=image, target=_mount_dir(mounts_dir, mountpoint))
    return result
