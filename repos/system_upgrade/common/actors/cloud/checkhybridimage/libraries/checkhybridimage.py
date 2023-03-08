import os

from leapp import reporting
from leapp.libraries.common import rhui
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import FirmwareFacts, HybridImage, InstalledRPM

BIOS_PATH = '/boot/grub2/grubenv'
EFI_PATH = '/boot/efi/EFI/redhat/grubenv'


def is_grubenv_symlink_to_efi():
    """
    Check whether '/boot/grub2/grubenv' is a relative symlink to
    '/boot/efi/EFI/redhat/grubenv'.
    """
    return os.path.islink(BIOS_PATH) and os.path.realpath(BIOS_PATH) == os.path.realpath(EFI_PATH)


def is_azure_agent_installed():
    """Check whether 'WALinuxAgent' package is installed."""
    src_ver_major = get_source_major_version()

    family = rhui.RHUIFamily(rhui.RHUIProvider.AZURE)
    azure_setups = rhui.RHUI_SETUPS.get(family, [])

    agent_pkg = None
    for setup in azure_setups:
        if setup.os_version == src_ver_major:
            agent_pkg = setup.extra_info.get('agent_pkg')
            break

    if not agent_pkg:
        return False

    return has_package(InstalledRPM, agent_pkg)


def is_bios():
    """Check whether system is booted into BIOS"""
    ff = next(api.consume(FirmwareFacts), None)
    return ff and ff.firmware == 'bios'


def check_hybrid_image():
    """Check whether the system is using Azure hybrid image."""
    if all([is_grubenv_symlink_to_efi(), is_azure_agent_installed(), is_bios()]):
        api.produce(HybridImage(detected=True))
        reporting.create_report([
            reporting.Title(
                'Azure hybrid (BIOS/EFI) image detected. "grubenv" symlink will be converted to a regular file'
            ),
            reporting.Summary(
                'Leapp detected the system is running on Azure cloud, booted using BIOS and '
                'the "/boot/grub2/grubenv" file is a symlink to "../efi/EFI/redhat/grubenv". In case of such a '
                'hybrid image scenario GRUB is not able to locate "grubenv" as it is a symlink to different '
                'partition and fails to boot. If the system needs to be run in EFI mode later, please re-create '
                'the relative symlink again.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.PUBLIC_CLOUD]),
        ])
