from leapp.actors import Actor
from leapp.libraries.actor import networkdeprecations
from leapp.models import IfCfg, NetworkManagerConnection, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckNetworkDeprecations(Actor):
    """
    Ensures that network configuration doesn't rely on unsupported settings

    Inhibits upgrade if the network configuration would not work with
    NetworkManager on the upgraded system due functionality being deprecated.

    Includes check for insecure wireless network encryption configuration
    what will not work with RHEL9.
    """

    name = "network_deprecations"
    consumes = (IfCfg, NetworkManagerConnection,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        networkdeprecations.process()
