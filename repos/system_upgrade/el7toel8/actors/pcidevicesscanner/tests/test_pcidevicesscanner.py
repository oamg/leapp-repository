from leapp.models import PCIDevices, PCIDevice
from leapp.libraries.actor.pcidevicesscanner import parse_pci_devices, produce_pci_devices


def test_parse_pci_devices(current_actor_libraries):
    devices = [
        '00:00.0 "Host bridge" "Intel Corporation" "440FX - 82441FX PMC [Natoma]" -r02 "Red Hat, Inc." '
        '"Qemu virtual machine"',
        '00:01.0 "ISA bridge" "Intel Corporation" "82371SB PIIX3 ISA [Natoma/Triton II]" "Red Hat, Inc." '
        '"Qemu virtual machine"',
        '00:01.1 "IDE interface" "Intel Corporation" "82371SB PIIX3 IDE [Natoma/Triton II]" -p80 "Red Hat, '
        'Inc." "Qemu virtual machine"']

    output = parse_pci_devices(devices)
    assert isinstance(output, list)
    assert len(output) == 3

    dev = output.pop()
    assert dev.slot == '00:01.1'
    assert dev.dev_cls == 'IDE interface'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '82371SB PIIX3 IDE [Natoma/Triton II]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'
    assert dev.progif == '80'

    dev = output.pop()
    assert dev.slot == '00:01.0'
    assert dev.dev_cls == 'ISA bridge'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '82371SB PIIX3 ISA [Natoma/Triton II]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'

    dev = output.pop()
    assert dev.slot == '00:00.0'
    assert dev.dev_cls == 'Host bridge'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '440FX - 82441FX PMC [Natoma]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'
    assert dev.rev == '02'


def test_parse_empty_list(current_actor_libraries):
    output = parse_pci_devices([])
    assert isinstance(output, list)
    assert not output


def test_parse_unknown_optional_parameter(current_actor_libraries):
    devices = ['00:01.1 -a01 "IDE interface" -b02 "Intel Corporation" -c03 "82371SB PIIX3 IDE [Natoma/Triton II]" '
               '-p80 "Red Hat, Inc." -d04 "Qemu virtual machine"']

    output = parse_pci_devices(devices)
    assert isinstance(output, list)
    assert len(output) == 1

    dev = output.pop()
    assert dev.slot == '00:01.1'
    assert dev.dev_cls == 'IDE interface'
    assert dev.vendor == 'Intel Corporation'
    assert dev.name == '82371SB PIIX3 IDE [Natoma/Triton II]'
    assert dev.subsystem_vendor == 'Red Hat, Inc.'
    assert dev.subsystem_name == 'Qemu virtual machine'
    assert dev.progif == '80'


def test_produce_pci_devices(current_actor_libraries):
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
            rev='02'),
        PCIDevice(
            slot='00:01.0',
            dev_cls='ISA bridge',
            vendor='Intel Corporation',
            name='82371SB PIIX3 ISA [Natoma/Triton II]',
            subsystem_vendor='Red Hat, Inc.',
            subsystem_name='Qemu virtual machine'),
        PCIDevice(
            slot='00:01.1',
            dev_cls='IDE interface',
            vendor='Intel Corporation',
            name='82371SB PIIX3 IDE [Natoma/Triton II]',
            subsystem_vendor='Red Hat, Inc.',
            subsystem_name='Qemu virtual machine',
            progif='80'),
    ]

    produce_pci_devices(fake_producer, devices)
    assert len(output) == 1
    assert len(output[0].devices) == 3


def test_produce_no_devices(current_actor_libraries):
    output = []

    def fake_producer(*args):
        output.extend(args)


    produce_pci_devices(fake_producer, [])
    assert len(output) == 1
    assert not output[0].devices


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(PCIDevices)
