from leapp.actors import Actor
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.models import InstalledRedHatSignedRPM
from leapp.libraries.common.rpms import has_package


class CheckDhclientActor(Actor):
    """
    Check if dhclient is installed
    and report backward incompatible change in CLI options.
    """

    name = "dhclient"
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if not has_package(InstalledRedHatSignedRPM, 'dhclient'):
            return

        create_report([
            reporting.Title('dhclient command line options changed'),
            reporting.Summary(
                'dhclient command line options have been changed '
                'since RHEL 7.7 release.'),
            reporting.Remediation(
                hint='If you have custom script which involves dhclient '
                'please check dhclient(8) man page for '
                '-I/-C options'),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Tags([reporting.Tags.NETWORK, reporting.Tags.TOOLS]),
            reporting.RelatedResource('package', 'dhclient')
        ])
