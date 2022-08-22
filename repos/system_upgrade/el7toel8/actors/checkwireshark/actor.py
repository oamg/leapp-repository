from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, Report
from leapp.reporting import create_report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckWireshark(Actor):
    """
    Report a couple of changes in tshark usage
    """

    name = 'check_wireshark'
    consumes = (InstalledRedHatSignedRPM, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if has_package(InstalledRedHatSignedRPM, 'wireshark'):
            create_report([
                reporting.Title('tshark: CLI options and output changes'),
                reporting.Summary(
                    'The -C suboption for -N option for asynchronous DNS name resolution '
                    'has been completely removed from tshark. The reason for this is that '
                    'the asynchronous DNS resolution is now the only resolution available '
                    'so there is no need for -C. If you are using -NC with tshark in any '
                    'of your scripts, please remove it.'
                    '\n\n'
                    'When using -H option with capinfos, the output no longer shows MD5 hashes. '
                    'Now it shows SHA256 instead. SHA1 might get removed very soon as well. '
                    'If you use these output values, please change your scripts.'),
                reporting.Severity(reporting.Severity.LOW),
                reporting.Groups([reporting.Groups.MONITORING, reporting.Groups.SANITY, reporting.Groups.TOOLS]),
                reporting.RelatedResource('package', 'wireshark'),
            ])
