from leapp.workflows import Workflow
from leapp.workflows.phases import Phase
from leapp.workflows.flags import Flags
from leapp.workflows.tagfilters import TagFilter
from leapp.workflows.policies import Policies
from leapp.tags import IPUWorkflowTag, FactsPhaseTag, ChecksPhaseTag, \
    DownloadPhaseTag, InterimPreparationPhaseTag, InitRamStartPhaseTag, \
    LateTestsPhaseTag, PreparationPhaseTag, RPMUpgradePhaseTag, ApplicationsPhaseTag, ThirdPartyApplicationsPhaseTag, \
    FinalizationPhaseTag, FirstBootPhaseTag, ReportPhaseTag


class IPUWorkflow(Workflow):
    name = 'InplaceUpgrade'
    tag = IPUWorkflowTag
    short_name = 'ipu'
    description = '''The IPU workflow takes care of an in-place upgrade (IPU) of RHEL 7 to RHEL 8.'''

    class FactsCollectionPhase(Phase):
        '''Get information (facts) about the system (e.g. installed packages, configuration, ...).

        No decision should be done in this phase. Scan the system to get information you need and provide
        it to other actors in the following phases.
        '''
        name = 'FactsCollection'
        filter = TagFilter(FactsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ChecksPhase(Phase):
        '''Check upgradability of the system, produce user question if needed and produce output for the report.

        Check whether it is possible to upgrade the system and detect potential risks. It is not expected to get
        additional information about the system in this phase, but rather work with data provided by the actors from
        the FactsCollection. When a potential risk is detected for upgrade, produce messages for the Reports phase.
        '''
        name = 'Checks'
        filter = TagFilter(ChecksPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ReportsPhase(Phase):
        '''Provide user with the result of the checks.'''
        name = 'Reports'
        filter = TagFilter(ReportPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    # The following two phases have been removed but are kept here for reference or in case they are needed again

    #class AttachPackageReposPhase(Phase):
    #    name = 'AttachPackageRepos'
    #    #NOTE: in case of use the AttachPackageReposPhaseTag tag has to be created
    #    filter = TagFilter(AttachPackageReposPhaseTag)
    #    policies = Policies(Policies.Errors.FailPhase,
    #                        Policies.Retry.Phase)
    #    flags = Flags()

    #class PlanningPhase(Phase):
    #    name = 'Planning'
    #    #NOTE: in case of use the PlanningPhaseTag tag has to be created
    #    filter = TagFilter(PlanningPhaseTag)
    #    policies = Policies(Policies.Errors.FailPhase,
    #                        Policies.Retry.Phase)
    #    flags = Flags()

    class DownloadPhase(Phase):
        '''Download data needed for the upgrade and prepare RPM transaction for the upgrade.'''
        name = 'Download'
        filter = TagFilter(DownloadPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class InterimPreparationPhase(Phase):
        '''Prepare an initial RAM file system (if required). Setup bootloader.'''
        name = 'InterimPreparation'
        filter = TagFilter(InterimPreparationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags(request_restart_after_phase=True)

    class InitRamStartPhase(Phase):
        '''Boot into the upgrade initramfs, mount disks, etc.'''
        name = 'InitRamStart'
        filter = TagFilter(InitRamStartPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    # The following two phases have been removed but are kept here for reference or in case they are needed again

    #class NetworkPhase(Phase):
    #    name = 'Network'
    #    #NOTE: in case of use the NetworkPhaseTag tag has to be created
    #    filter = TagFilter(NetworkPhaseTag)
    #    policies = Policies(Policies.Errors.FailPhase,
    #                        Policies.Retry.Phase)
    #    flags = Flags()

    #class StoragePhase(Phase):
    #    name = 'Storage'
    #    #NOTE: in case of use the StoragePhaseTag tag has to be created
    #    filter = TagFilter(StoragePhaseTag)
    #    policies = Policies(Policies.Errors.FailPhase,
    #                        Policies.Retry.Phase)
    #    flags = Flags()

    class LateTestsPhase(Phase):
        '''Last tests before the RPM upgrade that have to be done with the new kernel and systemd.'''
        name = 'LateTests'
        filter = TagFilter(LateTestsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class PreparationPhase(Phase):
        '''Prepare the environment to ascertain success of the RPM upgrade transaction.'''
        name = 'Preparation'
        filter = TagFilter(PreparationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class RPMUpgradePhase(Phase):
        '''Perform the RPM transaction, i.e. upgrade the RPMs.'''
        name = 'RPMUpgrade'
        filter = TagFilter(RPMUpgradePhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags(is_checkpoint=True)

    class ApplicationsPhase(Phase):
        '''Perform the neccessary steps to finish upgrade of applications provided by Red Hat.

        This may include moving/renaming of configuration files, modifying configuration of applications to be able
        to run correctly and with as similar behaviour to the original as possible.
        '''
        name = 'Applications'
        filter = TagFilter(ApplicationsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class ThirdPartyApplicationsPhase(Phase):
        '''Analogy to the Applications phase, but for third party and custom applications.'''
        name = 'ThirdPartyApplications'
        filter = TagFilter(ThirdPartyApplicationsPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()

    class FinalizationPhase(Phase):
        '''Additional actions that should be done before rebooting into the upgraded system.

        For example SELinux relabeling.
        '''
        name = 'Finalization'
        filter = TagFilter(FinalizationPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags(restart_after_phase=True)

    class FirstBootPhase(Phase):
        '''Actions to be done right after booting into the upgraded system.'''
        name = 'FirstBoot'
        filter = TagFilter(FirstBootPhaseTag)
        policies = Policies(Policies.Errors.FailPhase,
                            Policies.Retry.Phase)
        flags = Flags()
