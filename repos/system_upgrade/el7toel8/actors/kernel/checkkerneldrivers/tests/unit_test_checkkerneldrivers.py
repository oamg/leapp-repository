import pytest

from leapp.models import PCIDevice, PCIDevices, KernelModuleParameter
from leapp.reporting import Report


devices_ok = [
    PCIDevice(slot="00:00.0", dev_cls="foo", vendor="bar", name="foobar", driver="i915", pci_id="some id"),
    PCIDevice(slot="00:01.0", dev_cls="foo", vendor="bar", name="foobar", driver="serial", pci_id="some id"),
    PCIDevice(slot="00:02.0", dev_cls="foo", vendor="bar", name="foobar", driver="pcieport", pci_id="some id"),
    PCIDevice(slot="00:03.0", dev_cls="foo", vendor="bar", name="foobar", driver="nvme", pci_id="some id")
]
devices_driverless = [
    PCIDevice(slot="00:04.0", dev_cls="foo", vendor="bar", name="foobar", driver="", pci_id="some id"),
    PCIDevice(slot="00:05.0", dev_cls="foo", vendor="bar", name="foobar", driver="", pci_id="some id")
]
devices_removed = [
    PCIDevice(slot="00:06.0", dev_cls="foo", vendor="bar", name="foobar", driver="floppy", pci_id="some id"),
    PCIDevice(slot="00:07.0", dev_cls="foo", vendor="bar", name="foobar", driver="initio", pci_id="some id"),
    PCIDevice(slot="00:08.0", dev_cls="foo", vendor="bar", name="foobar", driver="pata_acpi", pci_id="some id"),
    PCIDevice(slot="00:09.0", dev_cls="foo", vendor="bar", name="foobar", driver="iwl4965", pci_id="some id")
]


@pytest.mark.parametrize("devices,expected", [
    ([], True),
    (devices_ok, True),
    (devices_driverless, True),
    (devices_ok + devices_driverless, True),
    (devices_removed, False),
    (devices_removed + devices_ok, False),
    (devices_removed + devices_driverless, False),
    (devices_ok + devices_removed + devices_driverless, False)])
def test_drivers(devices, expected, current_actor_context):
    """
    Tests CheckKernelDrivers actor by feeding it mocked PCI devices with their
    respective drivers, if they have one.  Actor should produce a report iff any
    mocked devices from devices_removed are fed to the actor, since their
    drivers are removed in RHEL8 (as per 'files/removed_drivers.txt').
    """
    current_actor_context.feed(PCIDevices(devices=devices))
    current_actor_context.run()
    if expected:
        assert not current_actor_context.consume(Report)
    else:
        assert current_actor_context.consume(Report)
