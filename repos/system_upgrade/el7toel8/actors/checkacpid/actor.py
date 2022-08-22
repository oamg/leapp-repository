from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import create_report, Report
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
            create_report([
                reporting.Title('Acpid incompatible changes in the next major version'),
                reporting.Summary('The option -d (debug) no longer implies -f (foreground).'),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Remediation(
                    hint='You must now use both options (\'-df\') for the same behavior. Please update '
                         'your scripts to be compatible with the changes.'),
                reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.SERVICES]),
                reporting.RelatedResource('package', 'acpid')
            ])
