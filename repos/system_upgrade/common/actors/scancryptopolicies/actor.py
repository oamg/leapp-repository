from leapp.actors import Actor
from leapp.libraries.actor import scancryptopolicies
from leapp.models import CryptoPolicyInfo
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCryptoPolicies(Actor):
    """
    Scan information about system wide set crypto policies including:
     * current crypto policy
     * installed custom crypto policies

    This information is, later in the process useful for the following:
     * copy the custom crypto policies files
     * notify user about the current setting and to review whether the policy still makes sense
       * it might be outdated and no longer meet the best security practices
       * if it is based on system policy such as DEFAULT, it might cause unexpected changes
    """

    name = 'scancryptopolicies'
    consumes = ()
    produces = (CryptoPolicyInfo,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scancryptopolicies.process()
