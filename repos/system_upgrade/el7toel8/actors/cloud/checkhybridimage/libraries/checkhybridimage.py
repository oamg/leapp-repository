import os

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRPM, HybridImage, FirmwareFacts
from leapp import reporting
from leapp.libraries.common import rhui


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
    arch = api.current_actor().configuration.architecture
    agent_pkg = rhui.RHUI_CLOUD_MAP[arch]['azure']['agent_pkg']
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
