from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation


class PowerTop(Actor):
    """
    Check if PowerTOP is installed. If yes, write information about non-compatible changes.
    """

    name = 'powertop'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(InstalledRedHatSignedRPM):
            for rpm in fact.items:
                if rpm.name == 'powertop':
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
                    break
