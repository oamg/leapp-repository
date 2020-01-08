import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import PCIDevices


def get_removed_drivers(path):
    removed = set()
    try:
        with open(path, 'r') as f:
            # Extracting kernel drivers from the file.
            for line in f.readlines():
                token = line.strip()
                if token.startswith('#') or not token:
                    # We do not want comments or empty lines.
                    continue
                removed.add(token)
        return removed
    except (IOError, OSError) as e:
        raise StopActorExecutionError('Cannot read {}: {}'.format(os.path.abspath(path), str(e)))


def get_present_drivers():
    return {device.driver for fact in api.consume(PCIDevices) for device in fact.devices if device.driver}


def check_drivers(removed, present):
    return removed & present
