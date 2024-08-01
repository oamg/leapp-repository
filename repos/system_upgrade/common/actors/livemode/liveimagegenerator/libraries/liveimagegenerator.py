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


DNF_CACHE_BACKUP_PATH = '/var/lib/leapp/dnf'


def clean_up_workspace_from_previous_builds(liveos_workspace):
    run(['rm', '-rf', liveos_workspace])
    os.makedirs(liveos_workspace)


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


def build_squashfs(context, livemode_config, userspace_info):
    """
    @Todo(mhecko): This is not used anymore, remove it. We now have the userspace image prepared, we just compress it.
    Generate the live rootfs image based on the target userspace

    :param livemode LiveModeConfigFacts: Livemode configuration message
    :param userspace_info TargetUserspaceInfo: Information about how target userspace is set up
    """
    liveos_workspace_path = livemode_config.temp_dir
    squashfs_fullpath = livemode_config.squashfs

    api.current_logger().info('Building the squashfs image %s using the temporary workspace %s',
                              squashfs_fullpath, liveos_workspace_path)

    clean_up_workspace_from_previous_builds(liveos_workspace_path)
    os.makedirs(os.path.join(liveos_workspace_path, 'LiveOS'))

    try:
        if os.path.exists(squashfs_fullpath):
            os.unlink(squashfs_fullpath)
    except OSError as error:
        api.current_logger().warning('Failed to remove already existing %s. Full error: %s',
                                     squashfs_fullpath, error)

    cwd = os.getcwd()
    try:
        with mounting.LoopMount(source=userspace_info.userspace_image_path,
                                target=liveos_workspace_path):
        # @Todo(mhecko): Can we build the image without changing the current directory?
            os.chdir(liveos_workspace_path)
            run(['mksquashfs', '.', squashfs_fullpath])
    except CalledProcessError as error:
        raise StopActorExecutionError(
           'Cannot pack the target userspace into a squash image. ',
           details={'details': 'The following error occurred while building the squashfs image: {0}.'.format(error)}
        )
    finally:
        os.chdir(cwd)

    try:
        run(['rm', '-rf', liveos_workspace_path])
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
        squashfs = build_squashfs(context, livemode_config, userspace_info)
        api.produce(LiveModeArtifacts(squashfs=squashfs))
