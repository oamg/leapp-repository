from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.libraries.common.reporting import report_with_remediation
from leapp.libraries.common.rpms import has_package
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckAcpid(Actor):
    """
    Check if acpid is installed. If yes, write information about non-compatible changes.
    """

    name = 'checkacpid'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'acpid'):
            report_with_remediation(
                title='Acpid incompatible changes in the next major version',
                summary='The option -d (debug) no longer implies -f (foreground).',
                remediation='You must now use both options (\'-df\') for the same behavior. Please update '
                            'your scripts to be compatible with the changes.',
                severity='low')
