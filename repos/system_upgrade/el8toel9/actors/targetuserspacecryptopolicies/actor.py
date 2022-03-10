from leapp.actors import Actor
from leapp.libraries.actor import targetuserspacecryptopolicies
from leapp.models import CryptoPolicyInfo, TargetUserSpaceInfo
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag

# TODO(pstodulk): move to common repo in future. This is something what should
# be in future generalized for all IPUs. But right now, we have blocking
# issues just for 8 -> 9.


class TargetUserspaceCryptoPolicies(Actor):
    """
    Set crypto policies inside the target userspace container.

    The crypto policies inside the container are "DEFAULT" by default, ignoring
    the setup on the host system. This leads to situations like when
    we work with rpms differently than the host system after the upgrade.
    The policies inside the container should reflect policies on the host
    system from the point of the target OS. E.g. when FIPS is used, we should
    not use DEFAULT, or when LEGACY is used, we should use the LEGACY as well.

    However, right now we are not able to handle systems with the custom crypto
    policies. In such a case the actor raises an error and upgrade is stopped.
    """

    name = 'target_userspace_crypto_policies'
    consumes = (CryptoPolicyInfo, TargetUserSpaceInfo)
    produces = ()
    tags = (IPUWorkflowTag, TargetTransactionChecksPhaseTag)

    def process(self):
        targetuserspacecryptopolicies.process()
