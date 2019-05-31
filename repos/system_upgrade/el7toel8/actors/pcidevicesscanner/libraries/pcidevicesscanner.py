import functools
import shlex

from leapp.libraries.stdlib import CalledProcessError, run
from leapp.models import PCIDevices, PCIDevice


def aslist(f):
    ''' Decorator used to convert generator to list '''
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def get_from_list(l, idx, default=''):
    ''' Get item at index from list or return a default '''
    try:
        ret = l[idx]
    except IndexError:
        ret = default

    return ret


@aslist
def parse_pci_devices(devices):
    ''' Parse lspci output and return a list of PCI devices '''
    for d in devices:
        raw = shlex.split(d)

        params = [r for r in raw if not r.startswith('-')]
        optionals = [r for r in raw if r.startswith('-')]

        rev = ''
        progif = ''
        for o in optionals:
            if o.startswith('-r'):
                rev = o.lstrip('-r')

            if o.startswith('-p'):
                progif = o.lstrip('-p')

        yield PCIDevice(
            slot=get_from_list(params, 0),
            dev_cls=get_from_list(params, 1),
            vendor=get_from_list(params, 2),
            name=get_from_list(params, 3),
            subsystem_vendor=get_from_list(params, 4),
            subsystem_name=get_from_list(params, 5),
            rev=rev,
            progif=progif
        )


def produce_pci_devices(producer, devices):
    ''' Produce a Leapp message with all PCI devices '''
    producer(PCIDevices(devices=devices))


def scan_pci_devices(producer):
    ''' Scan system PCI Devices '''
    try:
        output = run(['lspci', '-mm'], split=True)['stdout']
    except CalledProcessError:
        output = []

    devices = parse_pci_devices(output)
    produce_pci_devices(producer, devices)
