from leapp.actors import Actor
from leapp.libraries.actor import scanrhsm
from leapp.models import RHSMInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSubscriptionManagerInfo(Actor):
    """
    Scans the current system for subscription manager information

    Retrieves information about enabled and available repositories, attached SKUs, product certificates and release
    from the current system without modfying it.
    """

    name = 'scan_subscription_manager_info'
    consumes = ()
    produces = (RHSMInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scanrhsm.scan()
