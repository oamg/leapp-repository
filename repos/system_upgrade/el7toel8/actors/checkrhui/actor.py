from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import (
    InstalledRPM,
    RHUIInfo,
    RequiredTargetUserspacePackages,
)
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.common import rhsm, rhui


class CheckRHUI(Actor):
    """
    Check if system is using RHUI infrastructure (on public cloud) and send messages to
    provide additional data needed for upgrade.
    """

    name = 'checkrhui'
    consumes = (InstalledRPM)
    produces = (RHUIInfo, RequiredTargetUserspacePackages, Report)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for k, v in rhui.RHUI_CLOUD_MAP.items():
            if has_package(InstalledRPM, v['el7_pkg']):
                if not rhsm.skip_rhsm():
                    create_report([
                        reporting.Title('Upgrade initiated with RHSM on public cloud with RHUI infrastructure'),
                        reporting.Summary(
                            'Leapp detected this system is on public cloud with RHUI infrastructure '
                            'but the process was initiated without "--no-rhsm" command line option. '
                        ),
                        reporting.Severity(reporting.Severity.INFO),
                        reporting.Tags([reporting.Tags.PUBLIC_CLOUD]),
                    ])
                    return
                # AWS RHUI package is provided and signed by RH but the Azure one not
                if not has_package(InstalledRPM, v['leapp_pkg']):
                    create_report([
                        reporting.Title('Package "{}" is missing'.format(v['leapp_pkg'])),
                        reporting.Summary(
                            'On {} using RHUI infrastructure, a package "{}" is needed for'
                            'in-place upgrade'.format(k, v['leapp_pkg'])
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.RelatedResource('package', v['leapp_pkg']),
                        reporting.Flags([reporting.Flags.INHIBITOR]),
                        reporting.Tags([reporting.Tags.PUBLIC_CLOUD, reporting.Tags.RHUI]),
                        reporting.Remediation(commands=[['yum', 'install', '-y', v['leapp_pkg']]])
                    ])
                    return
                self.produce(RHUIInfo(provider=k))
                self.produce(RequiredTargetUserspacePackages(packages=[v['el8_pkg']]))
                return
