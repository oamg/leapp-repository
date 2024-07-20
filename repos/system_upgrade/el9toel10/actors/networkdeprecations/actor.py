from leapp import reporting
from leapp.actors import Actor
from leapp.models import NetworkManagerConfig, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNetworkDeprecations9to10(Actor):
    """
    Ensures that network configuration doesn't rely on unsupported settings

    Inhibits upgrade if the network configuration includes settings that
    could possibly not work on the upgraded system.

    Includes check for dhclient DHCP plugin that will be removed from RHEL10.
    """

    name = "network_deprecations"
    consumes = (NetworkManagerConfig,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    @staticmethod
    def report_dhclient():
        title = 'Deprecated DHCP plugin configured'
        summary = ('NetworkManager is configured to use the "dhclient" DHCP module.'
                   ' In Red Hat Enterprise Linux 10, this setting will be ignored'
                   ' along with any dhcp-client specific configuration.')
        remediation = ('Remove "dhcp=internal" line from "[main]" section from all'
                       ' configuration files in "/etc/NetworkManager". Review'
                       ' configuration in "/etc/dhcp", which will be ignored.')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Remediation(hint=remediation),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.NETWORK, reporting.Groups.SERVICES]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('package', 'dhcp-client'),
            reporting.RelatedResource('package', 'NetworkManager'),
        ])

    def process(self):
        for nm_config in self.consume(NetworkManagerConfig):
            self.log.info('Consuming dhcp={}'.format(nm_config.dhcp))
            if nm_config.dhcp == 'dhclient':
                CheckNetworkDeprecations9to10.report_dhclient()
