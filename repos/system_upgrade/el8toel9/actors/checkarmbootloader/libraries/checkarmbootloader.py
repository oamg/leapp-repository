from leapp.libraries.common.config.architecture import ARCH_ARM64, matches_architecture
from leapp.libraries.common.config.version import get_source_version, get_target_version, matches_target_version
from leapp.libraries.stdlib import api
from leapp.models import TargetUserSpacePreupgradeTasks

ARM_SHIM_PACKAGE_NAME = 'shim-aa64'
ARM_GRUB_PACKAGE_NAME = 'grub2-efi-aa64'


def process():
    """
    Check whether the upgrade path will use a target kernel compatible with the
    source bootloader on ARM systems. Prepare for a workaround otherwise.
    """

    if not matches_architecture(ARCH_ARM64):
        api.current_logger().info('Architecture not ARM. Skipping bootloader check.')
        return

    if matches_target_version('< 9.5'):
        api.current_logger().info((
            'Upgrade on ARM architecture on a compatible path ({} to {}). '
            'Skipping bootloader check.').format(get_source_version(), get_target_version()))
        return

    api.produce(
        TargetUserSpacePreupgradeTasks(
            install_rpms=[ARM_GRUB_PACKAGE_NAME, ARM_SHIM_PACKAGE_NAME]
        )
    )
