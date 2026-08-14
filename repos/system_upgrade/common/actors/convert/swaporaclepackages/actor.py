from leapp.actors import Actor
from leapp.libraries.actor import swaporaclepackages
from leapp.models import DNFWorkaround, TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, TargetTransactionFactsPhaseTag


class SwapOraclePackages(Actor):
    """
    Register a workaround to swap Oracle Linux packages before the DNF transaction.

    Some of native packages block an usual RPM transaction swap to their
    Red Hat counterparts:

    - the redhat-release pkg has a higher epoch than the RHEL's
      redhat-release, so DNF always treats it as "already installed" and never
      replaces it
    - oracle-(logos, indexhtml, backgrounds) Provide/Obsolete the unversioned
      packages, so they are resolved to the already installed so no swap is
      performed.

    Because these limitations cannot be worked around inside the main DNF
    transaction, we register a DNFWorkaround that runs inside the
    target userspace container against ``/installroot`` via ``dnf shell`` (see
    dnfplugin.apply_ol_packages_workaround). This actor only registers the script;
    it is executed later by the DNF transaction actors.

    Consuming TargetUserSpaceInfo ensures the workaround is registered only after
    the target userspace has been created.
    """

    name = 'swap_oracle_packages'
    consumes = (TargetUserSpaceInfo,)
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, TargetTransactionFactsPhaseTag)

    def process(self):
        swaporaclepackages.process()
