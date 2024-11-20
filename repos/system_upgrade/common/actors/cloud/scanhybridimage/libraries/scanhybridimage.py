import os

from leapp.libraries.common import rhui
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import FirmwareFacts, HybridImageAzure, InstalledRPM

EFI_MOUNTPOINT = '/boot/efi/'
AZURE_HYPERVISOR_ID = 'microsoft'

GRUBENV_BIOS_PATH = '/boot/grub2/grubenv'
GRUBENV_EFI_PATH = '/boot/efi/EFI/redhat/grubenv'


def scan_hybrid_image():
    """
    Check whether the system is using Azure hybrid image.
    """

    hybrid_image_condition_1 = is_azure_agent_installed() and is_bios()
    hybrid_image_condition_2 = has_efi_partition() and is_bios() and is_running_on_azure_hypervisor()

    if any([hybrid_image_condition_1, hybrid_image_condition_2]):
        api.produce(
            HybridImageAzure(
                grubenv_is_symlink_to_efi=is_grubenv_symlink_to_efi()
            )
        )


def is_azure_agent_installed():
    """
    Check whether 'WALinuxAgent' package is installed.
    """

    src_ver_major = get_source_major_version()

    family = rhui.RHUIFamily(rhui.RHUIProvider.AZURE)
    azure_setups = rhui.RHUI_SETUPS.get(family, [])

    agent_pkg = None
    for setup in azure_setups:
        setup_major_ver = str(setup.os_version[0])
        if setup_major_ver == src_ver_major:
            agent_pkg = setup.extra_info.get('agent_pkg')
            break

    if not agent_pkg:
        return False

    return has_package(InstalledRPM, agent_pkg)


def has_efi_partition():
    """
    Check whether ESP partition exists and is mounted.
    """

    return os.path.exists(EFI_MOUNTPOINT) and os.path.ismount(EFI_MOUNTPOINT)


def is_bios():
    """
    Check whether system is booted into BIOS
    """

    ff = next(api.consume(FirmwareFacts), None)
    return ff and ff.firmware == 'bios'


def is_running_on_azure_hypervisor():
    """
    Check if system is running on Azure hypervisor (Hyper-V)
    """

    return detect_virt() == AZURE_HYPERVISOR_ID


def detect_virt():
    """
    Detect execution in a virtualized environment
    """

    try:
        result = run(['systemd-detect-virt'])
    except CalledProcessError as e:
        api.current_logger().warning('Unable to detect virtualization environment! Error: {}'.format(e))
        return ''

    return result['stdout']


def is_grubenv_symlink_to_efi():
    """
    Check whether '/boot/grub2/grubenv' is a relative symlink to '/boot/efi/EFI/redhat/grubenv'.
    """

    is_symlink = os.path.islink(GRUBENV_BIOS_PATH)
    realpaths_match = os.path.realpath(GRUBENV_BIOS_PATH) == os.path.realpath(GRUBENV_EFI_PATH)

    return is_symlink and realpaths_match
