from leapp.actors import Actor
from leapp.libraries.actor import eap_repo_blocklist
from leapp.models import DistributionSignedRPM, RepositoriesSetupTasks
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class EapRepoBlocklist(Actor):
    """
    Check and handle EAP repos during RHEL in-place upgrade.

    Detects the installed EAP version (7.4, 8.1) from DistributionSignedRPM
    and produces RepositoriesSetupTasks to enable matching EAP repos and block
    conflicting ones on the target RHEL 9.
    EAP 7.4 enables both jb-eap-7.4-for-rhel-9 and jb-eap-7.4-els-for-rhel-9 repos.
    EAP 8.0 is not supported for leapp upgrade and will produce an inhibitor.
    """

    name = 'eap_repo_blocklist'
    consumes = (DistributionSignedRPM,)
    produces = (RepositoriesSetupTasks, Report)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        eap_repo_blocklist.process()
