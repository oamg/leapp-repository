from leapp.actors import Actor
from leapp.libraries.actor import restrictedpcisscanner
from leapp.models import RestrictedPCIDevices
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RestrictedPCIsScanner(Actor):
    """
    Provides data about restricted (unsupported or unavailable) PCI devices.

    Data gathered by querying the microservice mcs-el7-el8-unsupported-pcidevs.
    If the microservice is unavailable, then a local static json data is used.

    Note:
        In order to update local static json data form the online source
        you can enable test:
            unit_test_restricted_pcis_scanner.test_update_local_data
        by commenting the line:
            @pytest.mark.skip(reason="Use only for updating the local data")
        and running the test.
    """

    name = "restricted_pcis_scanner"
    consumes = ()
    produces = (RestrictedPCIDevices,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        restrictedpcisscanner.produce_restricted_pcis()
