from leapp.actors import Actor
from leapp.libraries.actor import swapdistropackagesworkaround
from leapp.models import DistributionSignedRPM, DNFWorkaround, TargetUserSpaceInfo, UsedTargetRepositories
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag


class SwapDistroPackagesWorkaround(Actor):
    """
    Prepare a workaround for swapping distribution packages the transaction cannot handle.

    Some packages block their target (RHEL) counterparts during the upgrade
    transaction, e.g. a same-named stub package pinned with a higher epoch or packages
    carrying unversioned Obsoletes/Provides. In such cases dnf reports the target
    package as "already installed" and the transaction fails.

    This actor downloads the target-distro builds of the affected packages from
    the enabled target repositories, generates a dnf shell instructions file that
    removes the blocking packages and installs the downloaded RPMs in a single
    transaction, and registers a DNFWorkaround executing those instructions with
    all repositories disabled just before the upgrade transaction.
    """

    name = 'swap_distro_packages_workaround'
    consumes = (DistributionSignedRPM, TargetUserSpaceInfo, UsedTargetRepositories)
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        swapdistropackagesworkaround.process()
