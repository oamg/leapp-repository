from leapp.actors import Actor
from leapp.libraries.common.reporting import report_with_remediation
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.models import InstalledRedHatSignedRPM
from leapp.libraries.common.rpms import has_package


class CheckDhclientActor(Actor):
    """
    Check if dhclient is installed
    and report backward incompatible change in CLI options
    """

    name = "dhclient"
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'dhclient'):
            title = 'dhclient command line options changed'
            summary = (
                'dhclient command line options have been changed '
                'since RHEL 7.7 release.'
            )
            remediation = (
                'If you have custom script which involves dhclient '
                'please check dhclient(8) man page for '
                '-I/-C options'
            )
            severity = 'low'
            report_with_remediation(title=title,
                                    severity=severity,
                                    remediation=remediation,
                                    summary=summary)
