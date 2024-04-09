from leapp.actors import Actor
from leapp.libraries.actor import removeleftoverpackages
from leapp.models import LeftoverPackages, RemovedPackages
from leapp.tags import ExperimentalTag, IPUWorkflowTag, RPMUpgradePhaseTag


class RemoveLeftoverPackages(Actor):
    """
    Remove packages left on the system after the upgrade to higher major version of RHEL.

    Removal of packages is necessary in order to keep the machine in supported state.
    Produce a message that is consumed by the `reportleftoverpackages` actor,
    which reports on the packages that have been removed.
    """

    name = 'remove_leftover_packages'
    consumes = (LeftoverPackages, )
    produces = (RemovedPackages, )
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag, ExperimentalTag, )

    def process(self):
        removeleftoverpackages.process()
