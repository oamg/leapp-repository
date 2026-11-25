from leapp.actors import Actor
from leapp.libraries.actor import dhcpservercheck
from leapp.models import DistributionSignedRPM, Report, SystemdServicesInfoSource
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DhcpServerCheck(Actor):
    """
    Check for the usage of ISC DHCP server.

    ISC DHCP (dhcp-server) has reached end-of-life and is not available in
    RHEL 10, where it is replaced by ISC Kea. Report a high severity message
    when the dhcp-server package is installed and the dhcpd service is enabled.
    """

    name = 'dhcp_server_check'
    consumes = (DistributionSignedRPM, SystemdServicesInfoSource)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        dhcpservercheck.process()
