from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import HybridImageAzure


def process():
    hybrid_image = next(api.consume(HybridImageAzure), None)

    if hybrid_image:
        reporting.create_report([
            reporting.Title(
                'Azure hybrid (BIOS/EFI) image detected. The GRUB configuration might be regenerated.'
            ),
            reporting.Summary(
                'Leapp detected that the system is running on Azure cloud and is booted using BIOS. '
                'While upgrading from older systems (i.e. RHEL 7) on such systems'
                'it is possible that the system might end up with invalid GRUB configuration, '
                'as `/boot/grub2/grub.cfg` might be overwritten by an old configuration from '
                '`/boot/efi/EFI/redhat/grub.cfg`, which might cause the system to fail to boot. '

                'Please ensure that the system is able to boot with both of these '
                'configurations. If an invalid configuration is detected during upgrade, '
                'it will be regenerated automatically using `grub2-mkconfig.`'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                reporting.Groups.PUBLIC_CLOUD,
                reporting.Groups.BOOT
            ]),
        ])
