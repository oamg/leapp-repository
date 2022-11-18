from leapp import reporting
from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.models import FirmwareFacts, GrubInfo
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

GRUB_SUMMARY = ('On legacy (BIOS) systems, GRUB core (located in the gap between the MBR and the '
                'first partition) does not get automatically updated when GRUB is upgraded.')


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
            if grub_info.orig_device_name:
                create_report([
                    reporting.Title(
                        'GRUB core will be updated during upgrade'
                    ),
                    reporting.Summary(GRUB_SUMMARY),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.BOOT]),
                ])
            else:
                create_report([
                    reporting.Title('Leapp could not identify where GRUB core is located'),
                    reporting.Summary(
                        'We assume GRUB core is located on the same device as /boot. Leapp needs to '
                        'update GRUB core as it is not done automatically on legacy (BIOS) systems. '
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.BOOT]),
                    reporting.Remediation(
                        hint='Please run "grub2-install <GRUB_DEVICE> command manually after upgrade'),
                ])
