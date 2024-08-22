from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import ConvertGrubenvTask, FirmwareFacts, HybridImageAzure


def process():
    hybrid_image = next(api.consume(HybridImageAzure), None)

    if not hybrid_image:
        return

    if not is_bios() or not hybrid_image.grubenv_is_symlink_to_efi:
        return

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
        reporting.Groups([
            reporting.Groups.PUBLIC_CLOUD,
            reporting.Groups.BOOT
        ]),
        reporting.RelatedResource('file', '/boot/grub2/grubenv'),
        reporting.RelatedResource('file', '/boot/efi/EFI/redhat/grubenv'),
    ])

    api.produce(ConvertGrubenvTask())


def is_bios():
    """
    Check whether system is booted into BIOS
    """

    ff = next(api.consume(FirmwareFacts), None)
    return ff and ff.firmware == 'bios'
