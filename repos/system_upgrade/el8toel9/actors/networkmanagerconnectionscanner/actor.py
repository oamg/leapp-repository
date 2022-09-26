from leapp.actors import Actor
from leapp.libraries.actor import networkmanagerconnectionscanner
from leapp.models import NetworkManagerConnection
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class NetworkManagerConnectionScanner(Actor):
    """
    Scan NetworkManager connection keyfiles
    """

    name = "network_manager_connection_scanner"
    consumes = ()
    produces = (NetworkManagerConnection,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        networkmanagerconnectionscanner.process()
