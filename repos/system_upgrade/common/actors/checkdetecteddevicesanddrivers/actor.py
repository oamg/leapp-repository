from leapp.actors import Actor
from leapp.libraries.actor import checkdddd
from leapp.models import DetectedDeviceOrDriver, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDetectedDevicesAndDrivers(Actor):
    """
    Checks whether or not detected devices and drivers are usable on the target system.

    In case a driver is no longer present in the target system, an inhibitor will be raised.
    If the device or driver is not maintained anymore, a warning report will be generated.
    """

    name = 'check_detected_devices_and_drivers'
    consumes = (DetectedDeviceOrDriver,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkdddd.process()
