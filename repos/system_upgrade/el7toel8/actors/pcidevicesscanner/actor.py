from leapp.actors import Actor
from leapp.libraries.actor import pcidevicesscanner
from leapp.models import PCIDevices
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class PCIDevicesScanner(Actor):
    name = 'pci_devices_scanner'
    description = 'Actor to provide information about all PCI devices.'
    consumes = ()
    produces = (PCIDevices,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)


    def process(self):
        self.produce(PCIDevices(
            devices=pcidevicesscanner.get_pci_devices()
        ))
