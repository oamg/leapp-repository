from leapp import reporting
from leapp.actors import Actor
from leapp.models import QuaggaToFrrFacts, Report
from leapp.reporting import create_report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

COMMON_REPORT_GROUPS = [
    reporting.Groups.NETWORK,
    reporting.Groups.SERVICES
]


class QuaggaReport(Actor):
    """
    Checking for babeld on RHEL-7.

    This actor is supposed to report that babeld was used on RHEL-7
    and it is no longer available in RHEL-8.
    """

    name = 'quagga_report'
    consumes = (QuaggaToFrrFacts, )
    produces = (Report, )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        try:
            quagga_facts = next(self.consume(QuaggaToFrrFacts))
        except StopIteration:
            return
        if 'babeld' in quagga_facts.active_daemons or 'babeld' in quagga_facts.enabled_daemons:
            create_report([
                reporting.Title('Babeld is not available in FRR'),
                reporting.ExternalLink(
                    url='https://access.redhat.com/'
                        'documentation/en-us/red_hat_enterprise_linux/8/html/'
                        'configuring_and_managing_networking/setting-your-rou'
                        'ting-protocols_configuring-and-managing-networking',
                    title='Setting routing protocols in RHEL8'),
                reporting.Summary(
                    'babeld daemon which was a part of quagga implementation in RHEL7 '
                    'is not available in RHEL8 in FRR due to licensing issues.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups(COMMON_REPORT_GROUPS + [reporting.Groups.INHIBITOR]),
                reporting.Remediation(hint='Please use RIP, OSPF or EIGRP instead of Babel')
            ])
        else:
            self.log.debug('babeld not used, moving on.')
