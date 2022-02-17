from leapp.actors import Actor
from leapp.libraries.actor import detectkerneldrivers
from leapp.models import ActiveKernelModulesFacts, DetectedDeviceOrDriver, DeviceDriverDeprecationData
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class DetectKernelDrivers(Actor):
    """
    Matches all currently loaded kernel drivers against known deprecated and removed drivers.
    """

    name = 'detect_kernel_drivers'
    consumes = (DeviceDriverDeprecationData, ActiveKernelModulesFacts)
    produces = (DetectedDeviceOrDriver,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        detectkerneldrivers.process()
