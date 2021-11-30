from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common import rhsm, rhui
from leapp.libraries.common.rpms import has_package
from leapp.models import (
    DNFPluginTask,
    InstalledRPM,
    KernelCmdlineArg,
    RequiredTargetUserspacePackages,
    RHUIInfo,
    RpmTransactionTasks
)
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRHUI(Actor):
    """
    Check if system is using RHUI infrastructure (on public cloud) and send messages to
    provide additional data needed for upgrade.
    """

    name = 'checkrhui'
    consumes = (InstalledRPM)
    produces = (
        KernelCmdlineArg,
        RHUIInfo,
        RequiredTargetUserspacePackages,
        Report, DNFPluginTask,
        RpmTransactionTasks,
    )
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        arch = self.configuration.architecture
        for provider, info in rhui.RHUI_CLOUD_MAP[arch].items():
            if has_package(InstalledRPM, info['el7_pkg']):
                is_azure_sap = False
                azure_sap_pkg = rhui.RHUI_CLOUD_MAP[arch]['azure-sap']['el7_pkg']
                azure_nonsap_pkg = rhui.RHUI_CLOUD_MAP[arch]['azure']['el7_pkg']
                # we need to do this workaround in order to overcome our RHUI handling limitation
                # in case there are more client packages on the source system
                if 'azure' in info['el7_pkg'] and has_package(InstalledRPM, azure_sap_pkg):
                    is_azure_sap = True
                    provider = 'azure-sap'
                    info = rhui.RHUI_CLOUD_MAP[arch]['azure-sap']
                if not rhsm.skip_rhsm():
                    create_report([
                        reporting.Title('Upgrade initiated with RHSM on public cloud with RHUI infrastructure'),
                        reporting.Summary(
                            'Leapp detected this system is on public cloud with RHUI infrastructure '
                            'but the process was initiated without "--no-rhsm" command line option '
                            'which implies RHSM usage (valid subscription is needed).'
                        ),
                        reporting.Severity(reporting.Severity.INFO),
                        reporting.Tags([reporting.Tags.PUBLIC_CLOUD]),
                    ])
                    return
                # AWS RHUI package is provided and signed by RH but the Azure one not
                if not has_package(InstalledRPM, info['leapp_pkg']):
                    create_report([
                        reporting.Title('Package "{}" is missing'.format(info['leapp_pkg'])),
                        reporting.Summary(
                            'On {} using RHUI infrastructure, a package "{}" is needed for'
                            'in-place upgrade'.format(provider.upper(), info['leapp_pkg'])
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.RelatedResource('package', info['leapp_pkg']),
                        reporting.Flags([reporting.Flags.INHIBITOR]),
                        reporting.Tags([reporting.Tags.PUBLIC_CLOUD, reporting.Tags.RHUI]),
                        reporting.Remediation(commands=[['yum', 'install', '-y', info['leapp_pkg']]])
                    ])
                    return
                # there are several "variants" related to the *AWS* provider (aws, aws-sap)
                if provider.startswith('aws'):
                    # We have to disable Amazon-id plugin in the initramdisk phase as the network
                    # is down at the time
                    self.produce(DNFPluginTask(name='amazon-id', disable_in=['upgrade']))
                # if RHEL7 and RHEL8 packages differ, we cannot rely on simply updating them
                if info['el7_pkg'] != info['el8_pkg']:
                    self.produce(RpmTransactionTasks(to_install=[info['el8_pkg']]))
                    self.produce(RpmTransactionTasks(to_remove=[info['el7_pkg']]))
                    if is_azure_sap:
                        self.produce(RpmTransactionTasks(to_remove=[azure_nonsap_pkg]))

                self.produce(RHUIInfo(provider=provider))
                self.produce(RequiredTargetUserspacePackages(packages=[info['el8_pkg']]))
                return
