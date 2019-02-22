from leapp.actors import Actor
from leapp.libraries.actor.scanner import detect_config_error
from leapp.models import GrubConfigError
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic
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
        error_detected = detect_config_error('/etc/default/grub')
        if error_detected:
            report_generic(
                title='Syntax error detected in grub configuration',
                summary='Syntax error was detected in GRUB_CMDLINE_LINUX value of grub configuration. '
                        'This error is causing booting and other issues. '
                        'Error is automatically fixed by add_upgrade_boot_entry actor.',
                severity='low'
            )

        self.produce(GrubConfigError(error_detected=error_detected))
