from leapp.actors import Actor
from leapp.libraries.actor import checkrhsmsku
from leapp.models import Report, RHSMInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRedHatSubscriptionManagerSKU(Actor):
    """
    Ensure the system is subscribed to the subscription manager

    This actor verifies that the system is correctly subscribed to via the Red Hat Subscription Manager and
    has attached SKUs. The actor will inhibit the upgrade if there are none and RHSM is not supposed
    to be skipped.
    """

    name = 'check_rhsmsku'
    consumes = (RHSMInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkrhsmsku.process()
