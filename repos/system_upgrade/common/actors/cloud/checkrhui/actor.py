import os

from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.common import rhsm, rhui
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
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
from leapp.reporting import create_report, Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


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
        TargetUserSpacePreupgradeTasks,
        CopyFile,
    )
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        upg_path = rhui.get_upg_path()
        for provider, info in rhui.RHUI_CLOUD_MAP[upg_path].items():
            if has_package(InstalledRPM, info['src_pkg']):
                # we need to do this workaround in order to overcome our RHUI handling limitation
                # in case there are more client packages on the source system
                if 'azure' in info['src_pkg']:
                    azure_sap_variants = [
                        'azure-sap',
                        'azure-sap-apps',
                    ]
                    for azure_sap_variant in azure_sap_variants:
                        sap_variant_info = rhui.RHUI_CLOUD_MAP[upg_path][azure_sap_variant]
                        if has_package(InstalledRPM, sap_variant_info['src_pkg']):
                            info = sap_variant_info
                            provider = azure_sap_variant

                if provider.startswith('google'):
                    rhui_dir = api.get_common_folder_path('rhui')
                    repofile = os.path.join(rhui_dir, provider, 'leapp-{}.repo'.format(provider))
                    api.produce(
                        TargetUserSpacePreupgradeTasks(
                            copy_files=[CopyFile(src=repofile, dst='/etc/yum.repos.d/leapp-google-copied.repo')]
                        )
                    )

                if not rhsm.skip_rhsm():
                    create_report([
                        reporting.Title('Upgrade initiated with RHSM on public cloud with RHUI infrastructure'),
                        reporting.Summary(
                            'Leapp detected this system is on public cloud with RHUI infrastructure '
                            'but the process was initiated without "--no-rhsm" command line option '
                            'which implies RHSM usage (valid subscription is needed).'
                        ),
                        reporting.Severity(reporting.Severity.INFO),
                        reporting.Groups([reporting.Groups.PUBLIC_CLOUD]),
                    ])
                    return

                # When upgrading with RHUI we cannot switch certs and let RHSM provide us repos for target OS content.
                # Instead, Leapp's provider-specific package containing target OS certs and repos has to be installed.
                if not has_package(InstalledRPM, info['leapp_pkg']):
                    create_report([
                        reporting.Title('Package "{}" is missing'.format(info['leapp_pkg'])),
                        reporting.Summary(
                            'On {} using RHUI infrastructure, a package "{}" is needed for'
                            'in-place upgrade'.format(provider.upper(), info['leapp_pkg'])
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.RelatedResource('package', info['leapp_pkg']),
                        reporting.Groups([reporting.Groups.INHIBITOR]),
                        reporting.Groups([reporting.Groups.PUBLIC_CLOUD, reporting.Groups.RHUI]),
                        reporting.Remediation(commands=[['yum', 'install', '-y', info['leapp_pkg']]])
                    ])
                    return

                # there are several "variants" related to the *AWS* provider (aws, aws-sap)
                if provider.startswith('aws'):
                    # We have to disable Amazon-id plugin in the initramdisk phase as the network
                    # is down at the time
                    self.produce(DNFPluginTask(name='amazon-id', disable_in=['upgrade']))

                # If source OS and target OS packages differ we must remove the source pkg, and install the target pkg.
                # If the packages do not differ, it is sufficient to upgrade them during the upgrade
                if info['src_pkg'] != info['target_pkg']:
                    self.produce(RpmTransactionTasks(to_install=[info['target_pkg']]))
                    self.produce(RpmTransactionTasks(to_remove=[info['src_pkg']]))
                    if provider in ('azure-sap', 'azure-sap-apps'):
                        azure_nonsap_pkg = rhui.RHUI_CLOUD_MAP[upg_path]['azure']['src_pkg']
                        self.produce(RpmTransactionTasks(to_remove=[azure_nonsap_pkg]))

                self.produce(RHUIInfo(provider=provider))
                self.produce(RequiredTargetUserspacePackages(packages=[info['target_pkg']]))
                return
