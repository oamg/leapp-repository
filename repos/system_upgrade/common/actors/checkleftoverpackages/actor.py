from leapp.actors import Actor
from leapp.libraries.actor import checkleftoverpackages
from leapp.models import InstalledUnsignedRPM, LeftoverPackages, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class CheckLeftoverPackages(Actor):
    """
    Check if there are any left over packages from older RHEL version present after upgrade.

    Actor produces message containing these packages.
    Message is empty if there are no packages from older system left.
    """

    name = 'check_leftover_packages'
    consumes = (TransactionCompleted, InstalledUnsignedRPM)
    produces = (LeftoverPackages,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        checkleftoverpackages.process()
