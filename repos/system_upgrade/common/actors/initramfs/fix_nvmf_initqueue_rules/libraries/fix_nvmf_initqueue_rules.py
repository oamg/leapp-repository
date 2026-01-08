import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig, NVMEInfo, TargetUserSpaceInfo, UpgradeInitramfsTasks

NVMF_DRACUT_MODULE_DIR = '/usr/lib/dracut/modules.d/95nvmf'
NVMF_INITQUEUE_RULES_FILENAME = '95-nvmf-initqueue.rules'
NVMF_INITQUEUE_RULES_PATH = os.path.join(NVMF_DRACUT_MODULE_DIR, NVMF_INITQUEUE_RULES_FILENAME)


def _get_rules_file_path():
    """
    Get the path to the fixed 95-nvmf-initqueue.rules file bundled with this actor.
    """
    return api.get_actor_file_path(NVMF_INITQUEUE_RULES_FILENAME)


def is_livemode_enabled() -> bool:
    livemode_config = next(api.consume(LiveModeConfig), None)
    if livemode_config and livemode_config.is_enabled:
        return True
    return False


def replace_nvmf_initqueue_rules():
    """
    Replace the nvmf dracut module's initqueue rules in the target userspace.
    """
    nvme_info = next(api.consume(NVMEInfo), None)
    if not nvme_info or not nvme_info.devices:
        api.current_logger().debug('No NVMe devices detected, skipping nvmf initqueue rules replacement.')
        return

    if is_livemode_enabled():
        api.current_logger().debug('LiveMode is enabled. Modifying initqueue stop condition is not required.')
        return

    userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    source_rules_path = _get_rules_file_path()

    target_rules_path = os.path.join(userspace_info.path, NVMF_INITQUEUE_RULES_PATH.lstrip('/'))
    target_dir = os.path.dirname(target_rules_path)

    # Check if the nvmf dracut module directory exists in the target userspace
    if not os.path.isdir(target_dir):
        api.current_logger().debug(
            'The nvmf dracut module directory {} does not exist in target userspace. '
            'Skipping rules replacement.'.format(target_dir)
        )
        return

    api.current_logger().info(
        'Replacing {} in target userspace with fixed version.'.format(NVMF_INITQUEUE_RULES_PATH)
    )

    try:
        shutil.copy2(source_rules_path, target_rules_path)
        api.current_logger().debug(
            'Successfully copied {} to {}'.format(source_rules_path, target_rules_path)
        )
    except (IOError, OSError) as e:
        raise StopActorExecutionError('Failed to copy nvmf initqueue rules to target userspace: {}'.format(e))

    api.produce(UpgradeInitramfsTasks())  # To enforce ordering of actors
