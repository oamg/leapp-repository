from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor.detectmissingnewlineingrubcfg import is_grub_config_missing_final_newline
from leapp.models import GrubConfigError
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DetectMissingNewlineInGrubCfg(Actor):
    """
    Check the grub configuration for a missing newline at its end.
    """

    name = 'detect_missing_newline_in_grub_cfg'
    consumes = ()
    produces = (Report, GrubConfigError)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        config = '/etc/default/grub'
        if is_grub_config_missing_final_newline(config):
            create_report([
                reporting.Title('Detected a missing newline at the end of grub configuration file.'),
                reporting.Summary(
                    'The missing newline in /etc/default/grub causes booting issues when appending '
                    'new entries to this file during the upgrade. Leapp will automatically fix this '
                    'problem by appending the missing newline to the grub configuration file.'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.BOOT]),
                reporting.RelatedResource('file', config)
            ])

            config_error = GrubConfigError(error_detected=True, error_type='missing newline')
            self.produce(config_error)
