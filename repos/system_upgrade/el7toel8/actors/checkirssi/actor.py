from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report, create_report
from leapp import reporting


class CheckIrssi(Actor):
    """
    Check if irssi is installed. If yes, write information about non-compatible changes.
    """

    name = 'checkirssi'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'irssi'):
            create_report([
                reporting.Title('Irssi incompatible changes in the next major version'),
                reporting.Summary(
                    'Disabled support for the insecure SSLv2 protocol.\n'
                    'Disabled SSLv3 due to the POODLE vulnerability.\n'
                    'Removing networks will now remove all attached servers and channels.\n'
                    'Removed --disable-ipv6 option.\n'
                ),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([
                        reporting.Groups.COMMUNICATION,
                        reporting.Groups.TOOLS
                ]),
                reporting.Remediation(hint='Please update your scripts to be compatible with the changes.'),
                reporting.RelatedResource('package', 'irssi')
            ])
