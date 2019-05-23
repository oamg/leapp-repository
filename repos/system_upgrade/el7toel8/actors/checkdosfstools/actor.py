from leapp.actors import Actor
from leapp.libraries.common.reporting import report_with_remediation
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDosfstools(Actor):
    """
    Check if dosfstools is installed. If yes, write information about non-compatible changes.
    """

    name = 'checkdosfstools'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'dosfstools'):
            report_with_remediation(
                title='Dosfstools incompatible changes in the next major version',
                summary='The automatic alignment of data clusters that was added in 3.0.8 and broken for '
                        'FAT32 starting with 3.0.20 has been reinstated. If you need to create file systems '
                        'for finicky devices that have broken FAT implementations use the option -a to '
                        'disable alignment.\n'
                        'The fsck.fat now defaults to interactive repair mode which previously had to be '
                        'selected with the -r option.\n',
                remediation='Please update your scripts to be compatible with the changes.',
                severity='low')
