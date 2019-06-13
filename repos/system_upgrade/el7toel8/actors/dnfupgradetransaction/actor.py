import shutil

from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.libraries.stdlib import run
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, TransactionCompleted, UsedTargetRepositories
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class DnfUpgradeTransaction(Actor):
    """
    Setup and call DNF upgrade command

    Based on previously calculated RPM transaction data, this actor will setup and call
    rhel-upgrade DNF plugin with necessary parameters
    """

    name = 'dnf_upgrade_transaction'
    consumes = (FilteredRpmTransactionTasks, TargetUserSpaceInfo, UsedTargetRepositories)
    produces = (TransactionCompleted,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        # FIXME: we hitting issue now because the network is down and rhsm
        # # is trying to connect to the server. Commenting this out for now
        # # so people will not be affected in case they do not have set a
        # # release and we will have time to fix it properly.
        # Make sure Subscription Manager OS Release is unset
        # cmd = ['subscription-manager', 'release', '--unset']
        # run(cmd)

        # FIXME: that's ugly hack, we should get info which file remove and
        # do it more nicely..
        run(['rm', '-f', '/etc/pki/product/69.pem'])

        used_repos = self.consume(UsedTargetRepositories)
        tasks = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        target_userspace_info = next(self.consume(TargetUserSpaceInfo), None)

        dnfplugin.perform_transaction_install(tasks=tasks, used_repos=used_repos,
                                              target_userspace_info=target_userspace_info)
        self.produce(TransactionCompleted())
        userspace = next(self.consume(TargetUserSpaceInfo), None)
        if userspace:
            try:
                shutil.rmtree(userspace.path)
            except EnvironmentError:
                self.log.info("Failed to remove temporary userspace - error ignored", exc_info=True)
