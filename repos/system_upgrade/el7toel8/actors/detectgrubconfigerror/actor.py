from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor.scanner import detect_config_error
from leapp.libraries.common.config import architecture
from leapp.models import GrubConfigError
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DetectGrubConfigError(Actor):
    """
    Check grub configuration for syntax error in GRUB_CMDLINE_LINUX value.
    """

    name = 'detect_grub_config_error'
    consumes = ()
    produces = (Report, GrubConfigError)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if architecture.matches_architecture(architecture.ARCH_S390X):
            # For now, skip just s390x, that's only one that is failing now
            # because ZIPL is used there
            return
        config = '/etc/default/grub'
        if detect_config_error(config):
            create_report([
                reporting.Title('Syntax error detected in grub configuration'),
                reporting.Summary(
                    'Syntax error was detected in GRUB_CMDLINE_LINUX value of grub configuration. '
                    'This error is causing booting and other issues. '
                    'Error is automatically fixed by add_upgrade_boot_entry actor.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.BOOT]),
                reporting.RelatedResource('file', config)
            ])

            config_error = GrubConfigError(error_detected=True,
                                           error_type='GRUB_CMDLINE_LINUX syntax')
            self.produce(config_error)
