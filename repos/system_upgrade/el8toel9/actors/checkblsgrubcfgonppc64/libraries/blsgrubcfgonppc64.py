from leapp import reporting
from leapp.libraries.common import grub
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import DefaultGrubInfo, FirmwareFacts, GrubCfgBios

URL = (
    'https://www.ibm.com/docs/en/linux-on-systems?topic=lpo-linux-distributions-virtualization'
    '-options-power8-power9-linux-power-systems'
)
TITLE = 'Linux distributions and virtualization options for POWER8 and POWER9 Linux on Power systems'


def process():
    default_grub_msg = next(api.consume(DefaultGrubInfo), None)
    grub_cfg = next(api.consume(GrubCfgBios), None)
    ff = next(api.consume(FirmwareFacts), None)
    if None in (default_grub_msg, grub_cfg):
        api.current_logger().debug(
            'Skipping execution. No DefaultGrubInfo and GrubCfgBios messages have '
            'been produced'
        )
        return

    if not architecture.matches_architecture(architecture.ARCH_PPC64LE):
        return

    if ff and ff.ppc64le_opal:
        reporting.create_report([
            reporting.Title(
                'Leapp cannot continue with upgrade on "ppc64le" bare metal systems'
            ),
            reporting.Summary(
                'In-place upgrade to RHEL 9 is not supported on POWER8 and POWER9 bare metal systems. '
                'For more information, refer to the following article: {}'.format(URL)
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(['inhibitor']),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.ExternalLink(
                url=URL,
                title=TITLE
            )
        ])

    if (
        not grub_cfg.insmod_bls and grub.is_blscfg_enabled_in_defaultgrub(default_grub_msg)
    ):
        reporting.create_report([
            reporting.Title(
                'Leapp will execute "grub2-mkconfig" to fix BLS Grub configuration.'
            ),
            reporting.Summary(
                'On "ppc64le" systems with BLS enabled, the GRUB configuration is not '
                'properly converted after the upgrade and Leapp has to run "grub2-mkconfig" '
                '-o /boot/grub2/grub.cfg command in order to fix an issue with booting into '
                'the RHEL 8 kernel instead of RHEL 9.'

            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
        ])
