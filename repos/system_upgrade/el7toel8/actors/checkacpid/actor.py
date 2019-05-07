from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation


class CheckAcpid(Actor):
    """
    Check if acpid is installed. If yes, write information about non-compatible changes.
    """

    name = 'checkacpid'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(InstalledRedHatSignedRPM):
            for rpm in fact.items:
                if rpm.name == 'acpid':
                    report_with_remediation(
                        title='Acpid incompatible changes in the next major version',
                        summary='The option -d (debug) no longer implies -f (foreground).',
                        remediation='You must now use both options (\'-df\') for the same behavior. Please update your scripts to be '
                                    'compatible with the changes.',
                        severity='low')
                    break
