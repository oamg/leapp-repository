from leapp.actors import Actor
from leapp.libraries.actor import enablerhsmreposonrhel8
from leapp.models import UsedTargetRepositories
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class EnableRHSMReposOnRHEL8(Actor):
    """
    On the upgraded RHEL 8, set release and enable repositories that were used during the upgrade transaction.

    We are enabling those RHEL 8 repos that are equivalent to the enabled RHEL 7 ones available. The BaseOS and
    AppStream repos are enabled on RHEL 8 by default. Any other repository needs to be enabled specifically using
    the subscription-manager (RHSM) utility. In case some custom repo was used during the upgrade transaction,
    this won't be enabled by this actors as it is unknown to the subscription-manager.

    We need to overwrite any RHSM release that may have been set before the upgrade, e.g. 7.6. Reasons:
    - If we leave the old RHEL 7 release set, dnf calls on the upgraded RHEL 8 would fail.
    - If we merely unset the release, users might end up updating the system to a newer version than the upgrade
      was supposed to be upgrading to.
    """

    name = 'enable_rhsm_repos_on_rhel8'
    consumes = (UsedTargetRepositories,)
    produces = ()
    tags = (IPUWorkflowTag, FirstBootPhaseTag)

    def process(self):
        enablerhsmreposonrhel8.set_rhsm_release()
        enablerhsmreposonrhel8.enable_rhsm_repos()
