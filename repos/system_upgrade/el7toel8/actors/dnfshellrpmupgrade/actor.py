import shutil

from leapp.actors import Actor
from leapp.libraries.common import dnfplugin
from leapp.libraries.stdlib import run
from leapp.models import FilteredRpmTransactionTasks, TargetUserSpaceInfo, TransactionCompleted, UsedTargetRepositories
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class DnfShellRpmUpgrade(Actor):
    """
    Setup and call DNF upgrade command

    Based on previously calculated RPM transaction data, this actor will setup and call
    rhel-upgrade DNF plugin with necessary parameters
    """

    name = 'dnf_shell_rpm_upgrade'
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

        dnfplugin.perform_transaction_install()
        self.produce(TransactionCompleted())
        userspace = next(self.consume(TargetUserSpaceInfo), None)
        if userspace:
            try:
                shutil.rmtree(userspace.path)
            except EnvironmentError:
                self.log.info("Failed to remove temporary userspace - error ignored", exc_info=True)
