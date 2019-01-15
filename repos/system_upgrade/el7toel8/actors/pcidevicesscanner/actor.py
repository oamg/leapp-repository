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
        pcidevicesscanner.produce_pci_devices(self.produce)
