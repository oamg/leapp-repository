from leapp.snactor.fixture import current_actor_context
from leapp.reporting import Report
from leapp.models import KernelCmdlineArg, PersistentNetNamesFacts, Interface, PCIAddress


def test_actor_single_eth0(current_actor_context):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interface = [Interface(name="eth0", mac="52:54:00:0b:4a:6d", vendor="redhat",
                           driver="pcieport", pci_info=pci,
                           devpath="/devices/platform/usb/cdc-wdm0")]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_more_ethX(current_actor_context):
    pci1 = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    pci2 = PCIAddress(domain="0000", bus="3d", function="00", device="Serial controller")
    interface = [Interface(name="eth0", mac="52:54:00:0b:4a:6d", vendor="redhat",
                           driver="pcieport", pci_info=pci1,
                           devpath="/devices/platform/usb/cdc-wdm0"),
                 Interface(name="eth1", mac="52:54:00:0b:4a:6a", vendor="redhat",
                           driver="serial", pci_info=pci2,
                           devpath="/devices/hidraw/hidraw0")]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert 'inhibitor' in current_actor_context.consume(Report)[0].report['groups']


def test_actor_single_int_not_ethX(current_actor_context):
    pci = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    interface = [Interface(name="tap0", mac="52:54:00:0b:4a:60", vendor="redhat",
                           driver="pcieport", pci_info=pci,
                           devpath="/devices/platform/usb/cdc-wdm0")]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_ethX_and_not_ethX(current_actor_context):
    pci1 = PCIAddress(domain="0000", bus="3e", function="00", device="PCI bridge")
    pci2 = PCIAddress(domain="0000", bus="3d", function="00", device="Serial controller")
    interface = [Interface(name="virbr0", mac="52:54:00:0b:4a:6d", vendor="redhat",
                           driver="pcieport", pci_info=pci1,
                           devpath="/devices/platform/usb/cdc-wdm0"),
                 Interface(name="eth0", mac="52:54:00:0b:4a:6a", vendor="redhat",
                           driver="serial", pci_info=pci2,
                           devpath="/devices/hidraw/hidraw0")]
    current_actor_context.feed(PersistentNetNamesFacts(interfaces=interface))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert 'inhibitor' in current_actor_context.consume(Report)[0].report['groups']
