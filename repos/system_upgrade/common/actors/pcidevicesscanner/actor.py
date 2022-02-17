from leapp.actors import Actor
from leapp.libraries.actor import pcidevicesscanner
from leapp.models import DetectedDeviceOrDriver, DeviceDriverDeprecationData, PCIDevices
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PCIDevicesScanner(Actor):
    """
    Provides data about existing PCI Devices.

    After collecting data from lspci, a message with relevant data will be produced.
    """

    name = 'pci_devices_scanner'
    consumes = (DeviceDriverDeprecationData,)
    produces = (PCIDevices, DetectedDeviceOrDriver)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        pcidevicesscanner.scan_pci_devices(self.produce)
