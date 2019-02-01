from leapp.actors import Actor
from leapp.models import Inhibitor, PCIDevices
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPCIDevices(Actor):
    """
    Check if any known unsupported PCI Device is in use. If yes, inhibit the upgrade process.

    Some PCI devices does not have necessary kernel module available in Red Hat Enterprise Linux 8
    what would prevent such device from working properly. At the time of writing this actor, LSI
    Logic SCSI Controllers suffer of such problem and if it's present on target system, upgrade
    process should not be executed.

    Test case table:
    +---------------------------++-----------------+
    | INPUT FACTORS             || BEHAVIORS       |
    +---------------------------++-----------------+
    | PCI Device                || Inhibit upgrade |
    +---------------------------++-----------------+
    | LSI Logic SCSI Controller || Yes             |
    | Any Other Device          || No              |
    +---------------------------++-----------------+
    """

    name = 'check_pci_devices'
    consumes = (PCIDevices,)
    produces = (Inhibitor,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        for data in self.consume(PCIDevices):
            for device in data.devices:
                if 'SCSI' in device.dev_cls and 'LSI Logic' in device.vendor:
                    self.produce(Inhibitor(
                        summary='LSI Logic SCSI Controller is not supported',
                        details='Kernel driver necessary for LSI Logic SCSI Controller (mpt*) '
                                'is not available in Red Hat Enterprise Linux 8. Since this '
                                'would prevent controller from working properly upgrade process '
                                'will be inhibited.',
                        solutions='Please consider disabling LSI Logic SCSI Controller if '
                                  'possible.'))
