from leapp.actors import Actor
from leapp.libraries.actor import customnetworkscripts
from leapp.models import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckCustomNetworkScripts(Actor):
    """
    Check the existence of custom network-scripts and warn user about possible
    manual intervention requirements.
    """

    name = "check_custom_network_scripts"
    produces = (Report,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        customnetworkscripts.process()
