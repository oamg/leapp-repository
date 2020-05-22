from leapp.actors import Actor
from leapp.libraries.common.rpms import has_package
from leapp.models import InstalledRedHatSignedRPM, RHUIInfo, RequiredTargetUserspacePackages, Report
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag



RHUI_CLOUD_MAP = {
    'aws': 'rh-amazon-rhui-client',
}


class CheckRHUI(Actor):
    """
    TBD
    """

    name = 'checkrhui'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (RHUIInfo, RequiredTargetUserspacePackages, Report)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for k, v in RHUI_CLOUD_MAP.items():
            if has_package(InstalledRedHatSignedRPM, v):
                self.produce(RHUIInfo(provider=k))
                self.produce(RequiredTargetUserspacePackages(packages=[v]))
                if not has_package(InstalledRedHatSignedRPM, 'leapp-rhui-aws'):
                    pass
                    # create report and inhibit
