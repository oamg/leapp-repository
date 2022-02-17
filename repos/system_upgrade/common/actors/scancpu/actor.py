from leapp.actors import Actor
from leapp.libraries.actor import scancpu
from leapp.models import CPUInfo, DetectedDeviceOrDriver, DeviceDriverDeprecationData
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCPU(Actor):
    """Scan CPUs of the machine."""

    name = 'scancpu'
    consumes = (DeviceDriverDeprecationData,)
    produces = (CPUInfo, DetectedDeviceOrDriver)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self, *args, **kwargs):
        scancpu.process()
