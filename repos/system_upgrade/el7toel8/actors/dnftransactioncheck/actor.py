from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, UsedTargetRepositories, XFSPresence
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class DnfTransactionCheck(Actor):
    """
    This actor tries to solve the RPM transaction to verify the all package dependencies can be successfully resolved.
    """

    name = 'dnf_transaction_check'
    consumes = (UsedTargetRepositories, FilteredRpmTransactionTasks, TargetUserSpaceInfo, XFSPresence)
    produces = ()
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):

        presence = next(self.consume(XFSPresence), XFSPresence())
        xfs_present = presence.present and presence.without_ftype
        used_repos = self.consume(UsedTargetRepositories)
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)

        if target_userspace_info:
            dnfplugin.perform_transaction_check(tasks=tasks, used_repos=used_repos,
                                                target_userspace_info=target_userspace_info, xfs_present=xfs_present)
