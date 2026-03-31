from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture, is_conversion
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultGrubInfo

GRUB_CFG_PATH = '/boot/grub2/grub.cfg'


def process():
    if architecture.matches_architecture(architecture.ARCH_S390X):
        return

    if not is_conversion():
        return

    default_grub_msg = next(api.consume(DefaultGrubInfo), None)
    if not default_grub_msg:
        api.current_logger().warning('No DefaultGrubInfo message, skipping GRUB config regeneration.')
        return

    if not grub.is_blscfg_enabled_in_defaultgrub(default_grub_msg):
        return

    api.current_logger().info('Conversion detected with BLS enabled, regenerating GRUB config')
    try:
        run(['grub2-mkconfig', '-o', GRUB_CFG_PATH])
    except CalledProcessError as e:
        api.current_logger().error('Failed to regenerate GRUB config: {}'.format(e))
