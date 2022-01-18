from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultGrubInfo, FirmwareFacts

GRUB_CFG_PATH = '/boot/grub2/grub.cfg'


def _is_grub_cfg_bls():
    # We do not want to use info from the GrubCfgBios model as it may not be valid
    # after the RPM upgrade transaction.

    with open(GRUB_CFG_PATH, 'r') as fo:
        grub_cfg = fo.read()
    if 'insmod blscfg' in grub_cfg:
        return True
    return False


def process():
    if not architecture.matches_architecture(architecture.ARCH_PPC64LE):
        return
    default_grub_msg = next(api.consume(DefaultGrubInfo), None)
    ff = next(api.consume(FirmwareFacts), None)
    if ff and ff.ppc64le_opal:
        return
    if (
        not _is_grub_cfg_bls() and
        grub.is_blscfg_enabled_in_defaultgrub(default_grub_msg)
    ):
        try:
            run(['grub2-mkconfig', '-o', GRUB_CFG_PATH])
        except CalledProcessError as e:
            api.current_logger().error(
                'Command grub2-mkconfig -o {} failed: {}'.format(GRUB_CFG_PATH, e)
            )
