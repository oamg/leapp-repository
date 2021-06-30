from leapp.actors import Actor
from leapp.libraries.actor import restrictedpcisscanner
from leapp.models import RestrictedPCIDevices
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RestrictedPCIsScanner(Actor):
    """
    Provides data about restricted (unsupported or/and unavailable) devices.

    The data sources priority set up is as following:
    1. The actor tries to get the data from /etc/leapp/files
    2. Then from the online service
    """

    name = "restricted_pcis_scanner"
    consumes = ()
    produces = (RestrictedPCIDevices,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        restrictedpcisscanner.produce_restricted_pcis()
