from leapp.actors import Actor
from leapp.libraries.actor import checkrhui as checkrhui_lib
from leapp.models import (
    CopyFile,
    DNFPluginTask,
    InstalledRPM,
    KernelCmdlineArg,
    RequiredTargetUserspacePackages,
    RHUIInfo,
    RpmTransactionTasks,
    TargetUserSpacePreupgradeTasks
)
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckRHUI(Actor):
    """
    Check if system is using RHUI infrastructure (on public cloud) and send messages to
    provide additional data needed for upgrade.
    """

    name = 'checkrhui'
    consumes = (InstalledRPM,)
    produces = (
        KernelCmdlineArg,
        RHUIInfo,
        RequiredTargetUserspacePackages,
        Report, DNFPluginTask,
        RpmTransactionTasks,
        TargetUserSpacePreupgradeTasks,
        CopyFile,
    )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        checkrhui_lib.process()
