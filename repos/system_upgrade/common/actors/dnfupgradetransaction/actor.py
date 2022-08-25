import shutil

from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.libraries.stdlib import run
from leapp.models import (
    DNFPluginTask,
    DNFWorkaround,
    FilteredRpmTransactionTasks,
    RHSMInfo,
    StorageInfo,
    TargetUserSpaceInfo,
    TransactionCompleted,
    UsedTargetRepositories,
    XFSPresence
)
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class DnfUpgradeTransaction(Actor):
    """
    Setup and call DNF upgrade command

    Based on previously calculated RPM transaction data, this actor will setup and call
    rhel-upgrade DNF plugin with necessary parameters
    """

    name = 'dnf_upgrade_transaction'
    consumes = (
        DNFPluginTask,
        DNFWorkaround,
        FilteredRpmTransactionTasks,
        RHSMInfo,
        StorageInfo,
        TargetUserSpaceInfo,
        UsedTargetRepositories,
        XFSPresence
    )
    produces = (TransactionCompleted,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        src_rhsm_info = next(self.consume(RHSMInfo), None)
        if src_rhsm_info:
            for prod_cert in src_rhsm_info.existing_product_certificates:
                run(['rm', '-f', prod_cert])

        used_repos = self.consume(UsedTargetRepositories)
        storage_info = next(self.consume(StorageInfo), None)
        plugin_info = list(self.consume(DNFPluginTask))
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)
        xfs_info = next(self.consume(XFSPresence), XFSPresence())

        dnfplugin.perform_transaction_install(
            tasks=tasks, used_repos=used_repos, storage_info=storage_info, target_userspace_info=target_userspace_info,
            plugin_info=plugin_info, xfs_info=xfs_info
        )
        self.produce(TransactionCompleted())
        userspace = next(self.consume(TargetUserSpaceInfo), None)
        if userspace:
            try:
                shutil.rmtree(userspace.path)
            except EnvironmentError:
                self.log.info("Failed to remove temporary userspace - error ignored", exc_info=True)
