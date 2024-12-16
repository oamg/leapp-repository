from leapp.actors import Actor
from leapp.libraries.actor import nonscarhsm
from leapp.models import Report, RHSMInfo
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRedHatSubscriptionManagerSCA(Actor):
    """
    Ensure that a registered system is in SCA (Simple Content Access)

    This actor verifies that in case the system is subscribed to the Red Hat
    Subscription Manager it is registered to an SCA organization. The actor
    will inhibit the upgrade if the system is registered to an entitlements
    organization.

    This actor will run regardless of whether the --skip-rhsm command line
    parameter is specified.
    """

    name = 'check_rhsmsca'
    consumes = (RHSMInfo,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        nonscarhsm.process()
