from leapp.actors import Actor
from leapp.libraries.actor import forcedefaultboot
from leapp.models import InstalledTargetKernelInfo
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class ForceDefaultBootToTargetKernelVersion(Actor):
    """
    Ensure the default boot entry is set to the new target kernel

    This Actor ensure that the default entry in the boot loader is set to the newly installed kernel version.
    There have been cases when the default boot entry was not set to the default kernel version. In this case the
    actor will log a warning for debugging purposes.
    """

    name = 'force_default_boot_to_target_kernel_version'
    consumes = (InstalledTargetKernelInfo,)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        forcedefaultboot.process()
