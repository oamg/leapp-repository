from leapp.actors import Actor
from leapp.libraries.actor.ipascanner import is_ipa_client_configured, is_ipa_server_configured
from leapp.libraries.common.rpms import has_package
from leapp.models import DistributionSignedRPM, IpaInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class IpaScanner(Actor):
    """
    Scan system for ipa-client and ipa-server status
    """

    name = "ipa_scanner"
    consumes = (DistributionSignedRPM,)
    produces = (IpaInfo,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        ipainfo = IpaInfo(
            has_client_package=has_package(
                DistributionSignedRPM, "ipa-client"
            ),
            is_client_configured=is_ipa_client_configured(),
            has_server_package=has_package(
                DistributionSignedRPM, "ipa-server"
            ),
            is_server_configured=is_ipa_server_configured(),
        )
        self.produce(ipainfo)
