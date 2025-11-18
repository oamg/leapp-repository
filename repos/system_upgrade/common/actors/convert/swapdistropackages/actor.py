from leapp.actors import Actor
from leapp.libraries.actor import swapdistropackages
from leapp.models import DistributionSignedRPM, RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SwapDistroPackages(Actor):
    """
    Swap distribution specific packages.

    Does nothing if not converting.
    """

    name = 'swap_distro_packages'
    consumes = (DistributionSignedRPM,)
    produces = (RpmTransactionTasks,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        swapdistropackages.process()
