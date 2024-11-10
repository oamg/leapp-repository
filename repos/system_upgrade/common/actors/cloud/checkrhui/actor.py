from leapp.actors import Actor
from leapp.configs.common.rhui import all_rhui_cfg
from leapp.libraries.actor import checkrhui as checkrhui_lib
from leapp.models import (
    CopyFile,
    DNFPluginTask,
    InstalledRPM,
    KernelCmdlineArg,
    RequiredTargetUserspacePackages,
    RHUIInfo,
    RpmTransactionTasks,
    TargetRepositories,
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
    config_schemas = all_rhui_cfg
    consumes = (InstalledRPM,)
    produces = (
        KernelCmdlineArg,
        RHUIInfo,
        RequiredTargetUserspacePackages,
        Report, DNFPluginTask,
        RpmTransactionTasks,
        TargetRepositories,
        TargetUserSpacePreupgradeTasks,
        CopyFile,
    )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        checkrhui_lib.process()
