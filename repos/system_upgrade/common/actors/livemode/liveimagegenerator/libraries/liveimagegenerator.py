import os
import os.path
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    LiveModeArtifacts,
    LiveModeConfigFacts,
    TargetUserSpaceInfo
)

LEAPP_LIVE_IMAGE = '/var/lib/leapp/live-upgrade.img'
LEAPP_LIVEOS_DIR = '/var/lib/leapp/tmp'
DEFAULT_XFS_SIZE = 3072  # MB


DNF_CACHE_BACKUP_PATH = '/var/lib/leapp/dnf'


def _backup_dnf_cache(context):
    """
    Move temporary the DNF cache outside the target userspace
    """
    try:
        shutil.move(context.full_path('/var/cache/dnf'), DNF_CACHE_BACKUP_PATH)
        context.makedirs('/var/cache/dnf')
    except OSError as error:
        api.current_logger().warning('Cannot backup the DNF cache. Full error: %s', error)


def _restore_dnf_cache(context):
    """
    Restore the DNF cache inside the target userspace
    """
    try:
        if os.path.isdir(context.full_path('/var/cache/dnf')):
            context.call(['rm', '-rf', '/var/cache/dnf'])
        shutil.move(DNF_CACHE_BACKUP_PATH, context.full_path('/var/cache/dnf'))
    except OSError:
        api.current_logger().warning('Cannot restore the DNF cache.')


def clean_up_workspace_from_previous_builds(liveos_workspace):
    run(['rm', '-rf', liveos_workspace])
    os.makedirs(liveos_workspace)


def _create_liveos_xfs_image(image_dest):
    """
    Create XFS image into LiveOS/rootfs.img
    """

    xfs_size = os.getenv('LEAPP_LIVE_XFS_SIZE', DEFAULT_XFS_SIZE)
    try:
        run(['mkfs.xfs', '-d', 'file,name={0},size={1}m'.format(image_dest, xfs_size)])
    except CalledProcessError as error:
        raise StopActorExecutionError('Cannot mkfs temporary LiveOS image.',
                                      details={'details': 'mkfs command failed - full error: {0}'.format(error)})


def _unmount_tmp_liveos(liveos_dir):
    try:
        run(['umount', '-fl', '{}_mnt'.format(liveos_dir)])
    except OSError:
        pass


def _copy_rootfs(userspace_dir, liveos_dir):
    """
    Copy the target userspace content into the XFS image
    """

    image_mnt_folder_name = '{0}_mnt'.format(os.path.basename(liveos_dir))
    live_image_mount_dir = os.path.join(os.path.dirname(liveos_dir), image_mnt_folder_name)
    try:
        os.makedirs(live_image_mount_dir)
        run(['mount', os.path.join(liveos_dir, '/LiveOS/rootfs.img'), live_image_mount_dir])
    except CalledProcessError as error:
        _unmount_tmp_liveos(liveos_dir)
        raise StopActorExecutionError(
           'Cannot mount temporary LiveOS image to populate it with target userspace.',
           details={'details': 'Full error: {0}'.format(error)}
        )

    try:
        # NOTE: this safe approach requires twice the target userspace size.
        # To avoid this, it would need an actor that creates this image
        # before the target userspace & mount it in /var/lib/leapp/elXuserspace
        # but it could cause issues with other actors that remove this directory
        # When mounted, its removal would lead to an EBUSY errno.
        api.current_logger().info('Copying the target userspace to the LiveOS')

        cmd = ['cp', '-fapZ', userspace_dir, live_image_mount_dir]
        run(cmd)
    except CalledProcessError as error:
        raise StopActorExecutionError('Failed to populate upgrade root fs image.',
                                      details={'details': 'Full error: {0}'.format(error)})
    finally:
        _unmount_tmp_liveos(liveos_dir)


def lighten_target_userpace(context):
    """
    Remove unneeded files from the target userspace.
    """

    userspace_trees_to_prune = ['artifacts', 'boot']

    for tree_to_prune in userspace_trees_to_prune:
        tree_full_path = os.path.join(context.base_dir, tree_to_prune)
        try:
            shutil.rmtree(tree_full_path)
        except OSError as error:
            api.current_logger().warning('Failed to remove /%s directory from the live image. Full error: %s',
                                         tree_to_prune, error)


def build_squashfs(context, livemode_config):
    """
    Generate the live rootfs image based on the target userspace

    :param livemode LiveModeConfigFacts: Livemode configuration message
    """
    liveos_workspace = livemode_config.temp_dir
    squashfs_fullpath = livemode_config.squashfs

    api.current_logger().info('Building the squashfs image %s using the temporary workspace %s',
                               squashfs_fullpath, liveos_workspace)

    clean_up_workspace_from_previous_builds(liveos_workspace)
    os.mkdirs(os.path.join(liveos_workspace, 'LiveOS'))

    if not livemode_config.with_cache:
        _backup_dnf_cache(context)

    upgrade_image_fullpath = os.path.join(liveos_workspace, 'LiveOS', 'root.img')
    _create_liveos_xfs_image(image_dest=upgrade_image_fullpath)
    _copy_rootfs(context.base_dir, liveos_workspace)

    try:
        os.unlink(squashfs_fullpath)
    except OSError as error:
        api.current_logger().warning('Failed to remove already existing %s. Full error: %s',
                                     squashfs_fullpath, error)

    cwd = os.getcwd()
    try:
        os.chdir(liveos_workspace)
        # @Todo(mhecko): Can we build the image without changing the current directory?
        run(['mksquashfs', '.', squashfs_fullpath])
    except CalledProcessError as error:
        raise StopActorExecutionError(
           'Cannot pack the target userspace into a squash image. ',
           details={'details': 'The following error occurred while building the squashfs image: {0}.'.format(error)}
        )
    finally:
        if not livemode_config.with_cache:
            _restore_dnf_cache(context)
        os.chdir(cwd)

    try:
        run(['rm', '-rf', liveos_workspace])

        # @Todo(mhecko): We are cleaning out the temporary workspace here, make sure that the upgrade image is not
        # in the workspace (misconfiguration)
    except OSError as error:
        api.current_logger().warning(
            'Failed to remove the temporary workspace (at %s) due to the following error: %s', error
        )

    return squashfs_fullpath


def generate_live_image_if_enabled():
    """
    Main function to generate the additional artifacts needed to run in live mode.
    """

    livemode_config = next(api.consume(LiveModeConfigFacts), None)
    if not livemode_config or not livemode_config.enabled:
        return

    userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    with mounting.NspawnActions(base_dir=userspace_info.path) as context:
        lighten_target_userpace(context)
        squashfs = build_squashfs(context, livemode_config)
        api.produce(LiveModeArtifacts(squashfs=squashfs))
