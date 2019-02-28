from leapp.actors import Actor
from leapp.libraries.actor.scanner import detect_config_error
from leapp.models import CheckResult, GrubConfigError
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DetectGrubConfigError(Actor):
    """
    Check grub configuration for syntax error in GRUB_CMDLINE_LINUX value.
    """

    name = 'detect_grub_config_error'
    consumes = ()
    produces = (CheckResult, GrubConfigError)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        error_detected = detect_config_error('/etc/default/grub')
        if error_detected:
            self.produce(CheckResult(
                severity='Info',
                result='Fixed',
                summary='Syntax error detected in grub configuration.',
                details='Syntax error was detected in GRUB_CMDLINE_LINUX value of grub configuration. '
                        'This error is causing booting and other issues. '
                        'Error is automatically fixed by add_upgrade_boot_entry actor.'
            ))

        self.produce(GrubConfigError(error_detected=error_detected))
