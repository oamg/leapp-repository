from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, UsedTargetRepositories
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag, ExperimentalTag


class DnfTransactionCheck(Actor):
    """
    This actor tries to solve the RPM transaction to verify the all package dependencies can be successfully resolved.
    """

    name = 'dnf_transaction_check'
    consumes = (UsedTargetRepositories, FilteredRpmTransactionTasks, TargetUserSpaceInfo)
    produces = ()
    tags = (IPUWorkflowTag, ChecksPhaseTag, ExperimentalTag)

    def process(self):
        dnfplugin.perform_transaction_check()
