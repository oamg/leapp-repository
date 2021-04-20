from leapp.actors import Actor
from leapp.libraries.actor.checkpcidrivers import checkpcidrivers_main
from leapp.models import PCIDevices, RestrictedPCIDevices
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPCIDrivers(Actor):
    """
    Check if host PCI devices drivers has restrictions on target system.

    If driver is restricted this means it is either unsupported or unavailable
    in some set of newer RHEL versions.

    If the driver is unavailable on a target system - then the upgrade will
        be inhibited
    If the driver is available, but not supported - then the upgrade will
        continue, but the relevant report will be generated
    If the driver is available and supported - then the upgrade will continue
        normally
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
