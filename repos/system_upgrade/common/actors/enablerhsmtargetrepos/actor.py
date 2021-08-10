from leapp.actors import Actor
from leapp.libraries.actor import enablerhsmtargetrepos
from leapp.models import UsedTargetRepositories
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class EnableRHSMTargetRepos(Actor):
    """
    On the upgraded target system, set release and enable repositories that were used during the upgrade
    transaction.

    We are enabling those RHEL target repos that are equivalent to the enabled source RHEL ones available.
    The BaseOS and AppStream repos are enabled on the target RHEL by default. Any other repository needs to
    be enabled specifically using the subscription-manager (RHSM) utility. In case some custom repo was used
    during the upgrade transaction, it won't be enabled by this actor as it is unknown to the subscription-manager.

    We need to overwrite any RHSM release that may have been set before the upgrade, e.g. 7.6. Reasons:
    - If we leave the old source RHEL release set, dnf calls on the upgraded target RHEL would fail.
    - If we merely unset the release, users might end up updating the system to a newer version than the upgrade
      was supposed to be upgrading to.
    """

    name = 'enable_rhsm_target_repos'
    consumes = (UsedTargetRepositories,)
    produces = ()
    tags = (IPUWorkflowTag, FirstBootPhaseTag)

    def process(self):
        enablerhsmtargetrepos.set_rhsm_release()
        enablerhsmtargetrepos.enable_rhsm_repos()
