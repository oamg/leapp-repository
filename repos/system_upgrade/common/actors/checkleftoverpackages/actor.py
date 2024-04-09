from leapp.actors import Actor
from leapp.libraries.actor import checkleftoverpackages
from leapp.models import InstalledUnsignedRPM, LeftoverPackages, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class CheckLeftoverPackages(Actor):
    """
    Check if there are any RHEL 7 packages present after upgrade.

    Actor produces message containing these packages. Message is empty if there are no el7 package left.
    """

    name = 'check_leftover_packages'
    consumes = (TransactionCompleted, InstalledUnsignedRPM)
    produces = (LeftoverPackages,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        checkleftoverpackages.process()
