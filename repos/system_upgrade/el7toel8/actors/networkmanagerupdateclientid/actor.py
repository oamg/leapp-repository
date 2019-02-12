from subprocess import CalledProcessError

from leapp.actors import Actor
from leapp.libraries.actor import networkmanagerupdateclientid
from leapp.libraries.stdlib import call
from leapp.models import NetworkManagerConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class NetworkManagerUpdateClientId(Actor):
    """
    Updates DHCP client-ids during Upgrade process.
    
    When using dhcp=dhclient on Red Hat Enterprise Linux 7, a non-hexadecimal client-id (a string)
    is sent on the wire as is (i.e. the first character is the 'type' as per RFC 2132 section
    9.14). On Red Hat Enterprise Linux 8, a zero byte is prepended to string-only client-ids. To
    preserve behavior on upgrade, we convert client-ids to the hexadecimal form.
    """

    name = 'network_manager_update_client_id'
    consumes = (NetworkManagerConfig,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        for nm_config in self.consume(NetworkManagerConfig):
            if nm_config.dhcp != '' and nm_config.dhcp != 'dhclient':
                self.log.info('DHCP client is {}, nothing to do'.format(nm_config.dhcp))
                return

            networkmanagerupdateclientid.update_client_ids(self.log)

            break


