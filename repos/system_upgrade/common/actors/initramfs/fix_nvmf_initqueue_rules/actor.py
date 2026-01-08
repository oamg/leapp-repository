from leapp.actors import Actor
from leapp.libraries.actor import fix_nvmf_initqueue_rules as fix_nvmf_initqueue_rules_lib
from leapp.models import LiveModeConfig, NVMEInfo, TargetUserSpaceInfo, UpgradeInitramfsTasks
from leapp.tags import InterimPreparationPhaseTag, IPUWorkflowTag


class FixNvmfInitqueueRules(Actor):
    """
    Replace nvmf dracut module's initqueue rules with a our own version.

    The original 95-nvmf-initqueue.rules file in the nvmf dracut module
    calls initqueue, which might not be running when the udev event lands.
    Therefore, we call `nvme connect-all` directly when when the udev event is triggered.
    """

    name = 'fix_nvmf_initqueue_rules'
    consumes = (LiveModeConfig, NVMEInfo, TargetUserSpaceInfo)
    produces = (UpgradeInitramfsTasks,)
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        fix_nvmf_initqueue_rules_lib.replace_nvmf_initqueue_rules()
