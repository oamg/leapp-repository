from leapp.actors import Actor
from leapp.libraries.actor import cryptopoliciescheck
from leapp.models import CryptoPolicyInfo, Report, TargetUserSpacePreupgradeTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CryptoPoliciesCheck(Actor):
    """
    This actor consumes previously gathered information about crypto policies on the source
    system and does two things:

     * warns user if the custom/legacy policy is used and whether there is time to review it
     * prepares the container by making sure it will have installed the tools for managing
       crypto policies and the custom policies are copied over to the intermediate and target
       systems
    """

    name = 'crypto_policies_check'
    consumes = (CryptoPolicyInfo,)
    produces = (TargetUserSpacePreupgradeTasks, Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag,)

    def process(self):
        cryptopoliciescheck.process(self.consume(CryptoPolicyInfo))
