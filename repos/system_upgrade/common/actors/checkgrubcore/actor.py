from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.models import FirmwareFacts, GrubInfo
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

GRUB_SUMMARY = ('On legacy (BIOS) systems, GRUB2 core (located in the gap between the MBR and the '
                'first partition) cannot be updated during the rpm transaction and Leapp has to initiate '
                'the update running "grub2-install" after the transaction. No action is needed before the '
                'upgrade. After the upgrade, it is recommended to check the GRUB configuration.')


class CheckGrubCore(Actor):
    """
    Check whether we are on legacy (BIOS) system and instruct Leapp to upgrade GRUB core
    """

    name = 'check_grub_core'
    consumes = (FirmwareFacts, GrubInfo)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if architecture.matches_architecture(architecture.ARCH_S390X):
            # s390x archs use ZIPL instead of GRUB
            return

        ff = next(self.consume(FirmwareFacts), None)
        if ff and ff.firmware == 'bios':
            grub_info = next(self.consume(GrubInfo), None)
            if not grub_info:
                raise StopActorExecutionError('Actor did not receive any GrubInfo message.')
            if grub_info.orig_devices:
                create_report([
                    reporting.Title(
                        'GRUB2 core will be automatically updated during the upgrade'
                    ),
                    reporting.Summary(GRUB_SUMMARY),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.BOOT]),
                ])
            else:
                create_report([
                    reporting.Title('Leapp could not identify where GRUB2 core is located'),
                    reporting.Summary(
                        'We assumed GRUB2 core is located on the same device(s) as /boot, '
                        'however Leapp could not detect GRUB2 on the device(s). '
                        'GRUB2 core needs to be updated maually on legacy (BIOS) systems. '
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.BOOT]),
                    reporting.Remediation(
                        hint='Please run "grub2-install <GRUB_DEVICE> command manually after the upgrade'),
                ])
