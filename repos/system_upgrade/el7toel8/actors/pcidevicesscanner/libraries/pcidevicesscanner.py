import re

from leapp.libraries.stdlib import api, run
from leapp.models import PCIDevice, PCIDevices

# Regex to capture Vendor, Device and SVendor and SDevice values
PCI_ID_REG = re.compile(r"(?<=Vendor:\t|Device:\t)\w+")


# TODO this could be solved more efficiently and error prune via python re
#   and groupdict
def parse_pci_device(textual_block, numeric_block):
    """ Parse one block from lspci output describing one PCI device """
    device = {
        'Slot': '',
        'Class': '',
        'Vendor': '',
        'Device': '',
        'SVendor': '',
        'SDevice': '',
        'PhySlot': '',
        'Rev': '',
        'ProgIf': '',
        'Driver': '',
        'Module': [],
        'NUMANode': ''
    }
    for line in textual_block.split('\n'):
        key, value = line.split(':\t')

        if key in device:
            if isinstance(device[key], list):
                device[key].append(value)
            else:
                if device[key]:
                    api.current_logger().debug(
                        'Unexpected duplicate key - {k}: {v} (current value: {vcurr}), ignoring'.format(
                            k=key, v=value, vcurr=device[key]))
                else:
                    device[key] = value
        else:
            api.current_logger().debug('Unrecognized key - {k}: {v}, ignoring'.format(k=key, v=value))

    return PCIDevice(
        slot=device['Slot'],
        dev_cls=device['Class'],
        vendor=device['Vendor'],
        name=device['Device'],
        subsystem_vendor=device['SVendor'],
        subsystem_name=device['SDevice'],
        physical_slot=device['PhySlot'],
        rev=device['Rev'],
        progif=device['ProgIf'],
        driver=device['Driver'],
        modules=device['Module'],
        numa_node=device['NUMANode'],
        pci_id=":".join(PCI_ID_REG.findall(numeric_block))
    )


def parse_pci_devices(pci_textual, pci_numeric):
    """ Parse lspci output and return a list of PCI devices """
    return [
        parse_pci_device(*block) for block
        in zip(
            pci_textual.split('\n\n')[:-1],
            pci_numeric.split('\n\n')[:-1]
        )
    ]


def produce_pci_devices(producer, devices):
    """ Produce a Leapp message with all PCI devices """
    producer(PCIDevices(devices=devices))


def scan_pci_devices(producer):
    """ Scan system PCI Devices """
    pci_textual = run(['lspci', '-vmmk'], checked=False)['stdout']
    pci_numeric = run(['lspci', '-vmmkn'], checked=False)['stdout']
    devices = parse_pci_devices(pci_textual, pci_numeric)
    produce_pci_devices(producer, devices)
