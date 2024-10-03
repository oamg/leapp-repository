from leapp.actors import Actor
from leapp.libraries.actor import emit_net_naming as emit_net_naming_lib
from leapp.models import (
    KernelCmdline,
    RpmTransactionTasks,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class EmitNetNamingScheme(Actor):
    """
    Emit necessary modifications of the upgrade environment and target command line to use net.naming-scheme.
    """
    name = 'emit_net_naming_scheme'
    consumes = (KernelCmdline,)
    produces = (
        RpmTransactionTasks,
        TargetKernelCmdlineArgTasks,
        TargetUserSpaceUpgradeTasks,
        UpgradeKernelCmdlineArgTasks,
    )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        emit_net_naming_lib.emit_msgs_to_use_net_naming_schemes()
