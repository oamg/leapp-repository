import functools
import os
import shlex
import subprocess
import six

from leapp.models import PCIDevice


def aslist(f):
    ''' Decorator used to convert generator to list '''
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def call(args, split=True):
    ''' Call external processes with some additional sugar '''
    r = None
    with open(os.devnull, mode='w') as err:
        if six.PY3:
            r = subprocess.check_output(args, stderr=err, encoding='utf-8')
        else:
            r = subprocess.check_output(args, stderr=err).decode('utf-8')
    if split:
        return r.splitlines()
    return r


def get_from_list(l, idx, default=''):
    ''' Get item at index from list or return a default '''
    try:
        ret = l[idx]
    except IndexError:
        ret = default

    return ret


@aslist
def get_pci_devices():
    ''' Get all PCI devices from system '''
    try:
        items = call(['lspci', '-mm'])
    except subprocess.CalledProcessError:
        items = []

    for i in items:
        raw = shlex.split(i)

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
            cls=get_from_list(params, 1),
            vendor=get_from_list(params, 2),
            name=get_from_list(params, 3),
            subsystem_vendor=get_from_list(params, 4),
            subsystem_name=get_from_list(params, 5),
            rev=rev,
            progif=progif
        )
