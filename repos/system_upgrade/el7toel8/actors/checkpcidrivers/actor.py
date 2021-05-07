from leapp.actors import Actor
from leapp.libraries.actor.checkpcidrivers import checkpcidrivers_main
from leapp.models import PCIDevices, RestrictedPCIDevices
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPCIDrivers(Actor):
    """
    Check if detected PCI devices are supported on a target system.

    Inhibit the ugprade if any detected drivers are unavailable on the target
    system.

    In case that all drivers are present on the target system but some of them
    becomes unsupported on the target system, create just report without the
    inhibitor.
    """

    name = "check_pci_drivers"
    consumes = (
        PCIDevices,
        RestrictedPCIDevices,
    )
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkpcidrivers_main()
