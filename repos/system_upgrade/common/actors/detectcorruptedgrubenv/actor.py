from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.config import architecture
from leapp.libraries.actor.detectcorruptedgrubenv import is_grubenv_corrupted
from leapp.models import GrubConfigError
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DetectCorruptedGrubenv(Actor):
    """
    Check the grubenv config file has a 1K size and don't end with a line feed
    """

    name = 'detect_corrupted_grubenv'
    consumes = ()
    produces = (Report, GrubConfigError)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if architecture.matches_architecture(architecture.ARCH_S390X):
            return
        configs = ['/boot/grub2/grubenv', '/boot/efi/EFI/redhat/grubenv']
        corrupted = []
        for cfg in configs:
            if is_grubenv_corrupted(cfg):
                corrupted.append(cfg)
        if corrupted:
            config = " and ".join(corrupted)
            create_report([
                reporting.Title('Detected a corrupted grubenv file.'),
                reporting.Summary(
                    'The grubenv file must be valid to pass the upgrade correctly: \n'
                    '- an exact size of 1024 bytes is expected \n'
                    '- it cannot end with a newline. \n'
                    'The corruption could be caused by a manual modification of the file which is not recommended.'
                ),
                reporting.Remediation(hint = 'Delete {} file(s) and regenerate grubenv using the grub2-mkconfig tool'.format(config)),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.BOOT]),
                reporting.Groups([reporting.Groups.INHIBITOR]),
                reporting.RelatedResource('file', config)
            ])

            config_error = GrubConfigError(error_detected=True, error_type='corrupted grubenv')
            self.produce(config_error)
