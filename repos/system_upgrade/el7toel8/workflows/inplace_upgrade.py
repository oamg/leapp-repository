from leapp.workflows import Workflow
from leapp.workflows.phases import Phase
from leapp.workflows.flags import Flags
from leapp.workflows.tagfilters import TagFilter
from leapp.workflows.policies import Policies
from leapp.tags import IPUWorkflowTag, FactsPhaseTag, ChecksPhaseTag, AttachPackageReposPhaseTag, PlanningPhaseTag, \
    DownloadPhaseTag, InterimPreparationPhaseTag, InitRamStartPhaseTag, NetworkPhaseTag, StoragePhaseTag, \
    LateTestsPhaseTag, PreparationPhaseTag, RPMUpgradePhaseTag, ApplicationsPhaseTag, ThirdPartyApplicationsPhaseTag, \
    FinalizationPhaseTag, FirstBootPhaseTag, ReportPhaseTag


class IPUWorkflow(Workflow):
    name = 'InplaceUpgrade'
    tag = IPUWorkflowTag
    short_name = 'ipu'
    description = '''No description has been provided for the InplaceUpgrade workflow.'''

    class FactsCollectionPhase(Phase):
        name = 'Facts collection'
        filter = TagFilter(FactsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ChecksPhase(Phase):
        name = 'Checks'
        filter = TagFilter(ChecksPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ReportsPhase(Phase):
        name = 'Reports'
        filter = TagFilter(ReportPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class AttachPackageReposPhase(Phase):
        name = 'AttachPackageRepos'
        filter = TagFilter(AttachPackageReposPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class PlanningPhase(Phase):
        name = 'Planning'
        filter = TagFilter(PlanningPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class DownloadPhase(Phase):
        name = 'Download'
        filter = TagFilter(DownloadPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class InterimPreparationPhase(Phase):
        name = 'InterimPreparation'
        filter = TagFilter(InterimPreparationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags(request_restart_after_phase=True)

    class InitRamStartPhase(Phase):
        name = 'InitRamStart'
        filter = TagFilter(InitRamStartPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class NetworkPhase(Phase):
        name = 'Network'
        filter = TagFilter(NetworkPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class StoragePhase(Phase):
        name = 'Storage'
        filter = TagFilter(StoragePhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class LateTestsPhase(Phase):
        name = 'LateTests'
        filter = TagFilter(LateTestsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class PreparationPhase(Phase):
        name = 'Preparation'
        filter = TagFilter(PreparationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class RPMUpgradePhase(Phase):
        name = 'RPMUpgrade'
        filter = TagFilter(RPMUpgradePhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ApplicationsPhase(Phase):
        name = 'Applications'
        filter = TagFilter(ApplicationsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ThirdPartyApplicationsPhase(Phase):
        name = 'ThirdPartyApplications'
        filter = TagFilter(ThirdPartyApplicationsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class FinalizationPhase(Phase):
        name = 'Finalization'
        filter = TagFilter(FinalizationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags(restart_after_phase=True)

    class FirstBootPhase(Phase):
        name = 'FirstBoot'
        filter = TagFilter(FirstBootPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()
