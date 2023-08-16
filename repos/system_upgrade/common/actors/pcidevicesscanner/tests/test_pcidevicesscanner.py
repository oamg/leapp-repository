import os

import pytest

from leapp.libraries.actor.pcidevicesscanner import parse_pci_devices, produce_pci_devices
from leapp.models import PCIDevice, PCIDevices


def test_parse_pci_devices():
    devices_textual = '''Slot:	00:00.0
Class:	Host bridge
Vendor:	Intel Corporation
Device:	440FX - 82441FX PMC [Natoma]
SVendor:	Red Hat, Inc.
SDevice:	Qemu virtual machine
PhySlot:	3
Rev:	02
NUMANode:	0

Slot:	00:01.0
Class:	ISA bridge
Vendor:	Intel Corporation
Device:	82371SB PIIX3 ISA [Natoma/Triton II]
SVendor:	Red Hat, Inc.
SDevice:	Qemu virtual machine

Slot:	00:01.1
Class:	IDE interface
Vendor:	Intel Corporation
Device:	82371SB PIIX3 IDE [Natoma/Triton II]
ProgIf:	80
Driver:	ata_piix
Module:	ata_piix
Module:	pata_acpi
Module:	ata_generic

'''
    devices_numeric = '''Slot:	00:00.0
Class:	Host bridge
Vendor:	15b45
Device:	0724
SVendor:	15b46
SDevice:	0725
PhySlot:	3
Rev:	02
NUMANode:	0

Slot:	00:01.0
Class:	ISA bridge
Vendor:	15b44
Device:	0723
SVendor:	15b50
SDevice:	0750

Slot:	00:01.1
Class:	IDE interface
Vendor:	15b43
Device:	0722
ProgIf:	80
Driver:	ata_piix
Module:	ata_piix
Module:	pata_acpi
Module:	ata_generic

'''

    output = parse_pci_devices(devices_textual, devices_numeric)
    assert isinstance(output, list)
    assert len(output) == 3

    dev = output.pop()
    assert dev.slot == '00:01.1'
    assert dev.dev_cls == 'IDE interface'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '82371SB PIIX3 IDE [Natoma/Triton II]'
    assert dev.progif == '80'
    assert dev.driver == 'ata_piix'
    assert dev.pci_id == '15b43:0722'
    assert len(dev.modules) == 3
    assert 'ata_piix' in dev.modules
    assert 'pata_acpi' in dev.modules
    assert 'ata_generic' in dev.modules

    dev = output.pop()
    assert dev.slot == '00:01.0'
    assert dev.dev_cls == 'ISA bridge'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '82371SB PIIX3 ISA [Natoma/Triton II]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'
    assert dev.driver == ''
    assert dev.modules == []
    assert dev.rev == ''
    assert dev.physical_slot == ''
    assert dev.numa_node == ''
    assert dev.pci_id == '15b44:0723:15b50:0750'

    dev = output.pop()
    assert dev.slot == '00:00.0'
    assert dev.dev_cls == 'Host bridge'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '440FX - 82441FX PMC [Natoma]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'
    assert dev.rev == '02'
    assert dev.physical_slot == '3'
    assert dev.numa_node == '0'
    assert dev.pci_id == '15b45:0724:15b46:0725'


def test_parse_empty_list():
    output = parse_pci_devices('', '')
    assert isinstance(output, list)
    assert not output


def test_parse_unknown_keys():
    devices_textual = '''Slot:	00:1c.0
Class:	PCI bridge
Material:	Silicon
Vendor:	Intel Corporation
Origin:	People's Republic of China
Device:	Sunrise Point-LP PCI Express Root Port #1
Flavor:	Burnt toast
Rev:	f1
Flavor:	Spicy beef
Driver:	pcieport

'''
    devices_numeric = '''Slot:	00:1c.0
Class:	PCI bridge
Material:	Silicon
Vendor:	15b74
Origin:	People's Republic of China
Device:	0724
Flavor:	Burnt toast
Rev:	f1
Flavor:	Spicy beef
Driver:	pcieport

'''

    output = parse_pci_devices(devices_textual, devices_numeric)
    assert isinstance(output, list)
    assert len(output) == 1

    dev = output.pop()
    assert dev.slot == '00:1c.0'
    assert dev.dev_cls == 'PCI bridge'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == 'Sunrise Point-LP PCI Express Root Port #1'
    assert dev.rev == 'f1'
    assert dev.driver == 'pcieport'
    assert dev.pci_id == '15b74:0724'
    assert dev.modules == []


def test_produce_pci_devices():
    output = []

    def fake_producer(*args):
        output.extend(args)

    devices = [
        PCIDevice(
            slot='00:00.0',
            dev_cls='Host bridge',
            vendor='Intel Corporation',
            name='440FX - 82441FX PMC [Natoma]',
            subsystem_vendor='Red Hat, Inc.',
            subsystem_name='Qemu virtual machine',
            pci_id='15b560:0739',
            rev='02'),
        PCIDevice(
            slot='00:01.0',
            dev_cls='ISA bridge',
            vendor='Intel Corporation',
            name='82371SB PIIX3 ISA [Natoma/Triton II]',
            subsystem_vendor='Red Hat, Inc.',
            pci_id='15b560:0739',
            subsystem_name='Qemu virtual machine'),
        PCIDevice(
            slot='00:01.1',
            dev_cls='IDE interface',
            vendor='Intel Corporation',
            name='82371SB PIIX3 IDE [Natoma/Triton II]',
            subsystem_vendor='Red Hat, Inc.',
            subsystem_name='Qemu virtual machine',
            pci_id='15b560:0739',
            progif='80'),
    ]

    produce_pci_devices(fake_producer, devices)
    assert len(output) == 1
    assert len(output[0].devices) == 3


def test_produce_no_devices():
    output = []

    def fake_producer(*args):
        output.extend(args)

    produce_pci_devices(fake_producer, [])
    assert len(output) == 1
    assert not output[0].devices


# TODO(pstodulk): update the test - drop current_actor_context and use monkeypatch
@pytest.mark.skipif(not os.path.exists('/usr/sbin/lspci'), reason='lspci not installed on the system')
def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(PCIDevices)
