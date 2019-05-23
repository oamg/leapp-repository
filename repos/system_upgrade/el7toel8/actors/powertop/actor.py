from leapp.actors import Actor
from leapp.libraries.common.reporting import report_with_remediation
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PowerTop(Actor):
    """
    Check if PowerTOP is installed. If yes, write information about non-compatible changes.
    """

    name = 'powertop'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'powertop'):
            report_with_remediation(
                title='PowerTOP compatibility options removed in the next major version',
                summary='The -d (dump) option which has been kept for RHEL backward compatibility has been '
                        'dropped.\n'
                        'The -h option which has been used for RHEL backward compatibility is no longer '
                        'alias for --html, but it\'s now an alias for --help to follow the upstream.\n'
                        'The -u option which has been used for RHEL backward compatibility as an alias for '
                        '--help has been dropped.\n',
                remediation='Please remove the dropped options from your scripts.',
                severity='low')
