from leapp.actors import Actor
from leapp.libraries.actor import networkdeprecations
from leapp.models import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckNetworkDeprecations(Actor):
    """
    Ensures that network configuration doesn't rely on unsupported settings

    Inhibits upgrade if the network configuration would not work with
    NetworkManager on the upgraded system due functionality being deprecated.

    Includes check for insecure wireless network encryption configuration
    what will not work with RHEL9.
    """

    name = "network_deprecations"
    produces = (Report,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        networkdeprecations.process()
