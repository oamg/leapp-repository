import re

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.architecture import ARCH_ACCEPTED
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import HybridImage

GRUB_CFG_PATH = '/boot/grub2/grub.cfg'

MATCH_ARCH = r'({})'.format('|'.join(ARCH_ACCEPTED))
MATCH_RHEL7_KERNEL_VERSION = r"\d+\.\d+\.\d+-\d+(\.\d+)*\.el7\.{}".format(MATCH_ARCH)
MATCH_RHEL7_KERNEL_DEFINITION = r"vmlinuz-{}".format(MATCH_RHEL7_KERNEL_VERSION)


def process():
    if not _is_hybrid_image():
        api.current_logger().info('System is not a hybrid image. Skipping.')
        return

    grubcfg = _read_grubcfg()
    if _is_grubcfg_invalid(grubcfg):
        _run_grub2_mkconfig()


def _is_hybrid_image():
    return next(api.consume(HybridImage), None) is not None


def _read_grubcfg():
    api.current_logger().debug('Reading {}:'.format(GRUB_CFG_PATH))
    with open(GRUB_CFG_PATH, 'r') as fin:
        grubcfg = fin.read()

    api.current_logger().debug(grubcfg)
    return grubcfg


def _is_grubcfg_invalid(grubcfg):
    return _contains_rhel7_kernel_definition(grubcfg)


def _contains_rhel7_kernel_definition(grubcfg):
    api.current_logger().debug("Looking for RHEL7 kernel version ...")

    match = re.search(MATCH_RHEL7_KERNEL_DEFINITION, grubcfg)

    api.current_logger().debug(
        "Matched: {}".format(match.group() if match else "[NO MATCH]")
    )

    return match is not None


def _run_grub2_mkconfig():
    api.current_logger().info("Regenerating {}".format(GRUB_CFG_PATH))

    try:
        run([
            'grub2-mkconfig',
            '-o',
            GRUB_CFG_PATH
        ])
    except CalledProcessError as err:
        msg = 'Could not regenerate {}: {}'.format(GRUB_CFG_PATH, str(err))
        api.current_logger().error(msg)
        raise StopActorExecutionError(msg)
