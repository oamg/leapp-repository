import pyudev

from leapp.models import PCIAddress, Interface
from leapp.libraries.stdlib import api

udev_context = pyudev.Context()


def physical_interfaces():
    """
    Returns a list of pyudev.Device objects for all physical network interfaces
    """
    enumerator = pyudev.Enumerator(udev_context).match_subsystem('net')
    return [d for d in enumerator if not d.device_path.startswith('/devices/virtual/')]


def pci_info(path):
    """
    Returns PCI topology info from string which is expected to be a value of ID_PATH udev device property
    """
    pci = {}

    # TODO(msekleta): check that path argument actually has ID_PATH format
    if path.startswith('pci-'):
        components = path[4:16].split(':')
        pci['domain'] = components[0]
        pci['bus'] = components[1]
        pci['device'] = components[2].split('.')[0]
        pci['function'] = components[2].split('.')[1]

    return pci


def interfaces():
    """
    Generator which produces an Interface objects containing assorted interface properties relevant for network naming
    """
    for dev in physical_interfaces():
        attrs = {}

        try:
            attrs['name'] = dev.sys_name
            attrs['devpath'] = dev.device_path
            attrs['driver'] = dev['ID_NET_DRIVER']
            attrs['vendor'] = dev['ID_VENDOR_ID']
            attrs['pci_info'] = PCIAddress(**pci_info(dev['ID_PATH']))
            attrs['mac'] = dev.attributes['address']
        except Exception as e:  # pylint: disable=broad-except
            # FIXME(msekleta): We should probably handle errors more granularly
            # Maybe we should inhibit upgrade process at this point
            api.current_logger().warning('Failed to gather information about network interface: ' + str(e))
            continue

        yield Interface(**attrs)
