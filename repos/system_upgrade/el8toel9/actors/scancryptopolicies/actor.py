from leapp.actors import Actor
from leapp.libraries.actor import scancryptopolicies
from leapp.models import CryptoPolicyInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCryptoPolicies(Actor):
    """
    Scan information about system wide set crypto policies
    """

    name = 'scancryptopolicies'
    consumes = ()
    produces = (CryptoPolicyInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scancryptopolicies.process()
