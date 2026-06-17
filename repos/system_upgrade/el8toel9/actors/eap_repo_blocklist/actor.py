from leapp.actors import Actor
from leapp.libraries.actor import eap_repo_blocklist
from leapp.models import DistributionSignedRPM, RepositoriesBlacklisted
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class EapRepoBlocklist(Actor):
    """
    Blocklist conflicting EAP repos during RHEL in-place upgrade.
    Detects the installed EAP version (7.4, 8.0, 8.1) from DistributionSignedRPM
    and produces RepositoriesBlacklisted to disable non-matching EAP repos for
    the target RHEL 9, preventing wrong package resolution during upgrade.
    """

    name = 'eap_repo_blocklist'
    consumes = (DistributionSignedRPM,)
    produces = (RepositoriesBlacklisted,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        eap_repo_blocklist.process()
