import json

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import fetch
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevices
from leapp.models.fields import ModelViolationError


try:
    # python3
    from json import JSONDecodeError  # pylint: disable=ungrouped-imports
except ImportError:
    # python2
    JSONDecodeError = ValueError

UNSUPPORTED_DRIVER_NAMES_FILE = "unsupported_driver_names.json"
UNSUPPORTED_PCI_IDS_FILE = "unsupported_pci_ids.json"


def produce_restricted_pcis():
    """
    Produce RestrictedPCIDevice message from the online or offline sources.

    The data sources preference order is the following:
    1. We try to get the data from the /etc/leapp/files
    2. We try to get the data from the only web service
    """
    unsupported_driver_names = {"devices": {}}
    unsupported_pci_ids = {"devices": {}}
    try:
        unsupported_driver_names = fetch.read_or_fetch(UNSUPPORTED_DRIVER_NAMES_FILE)
        unsupported_pci_ids = fetch.read_or_fetch(UNSUPPORTED_PCI_IDS_FILE)
        unsupported_driver_names = json.loads(unsupported_driver_names, encoding="utf-8")
        unsupported_pci_ids = json.loads(unsupported_pci_ids, encoding="utf-8")
    except (JSONDecodeError, UnicodeDecodeError):
        raise StopActorExecutionError("The required files have invalid JSON format and can't be decoded.")

    # trying to produce the message from received data
    try:
        api.produce(RestrictedPCIDevices.create({
                    "driver_names": tuple(unsupported_driver_names["devices"].values()),
                    "pci_ids": tuple(unsupported_pci_ids["devices"].values())}))
    # bad data format
    except (KeyError, AttributeError, TypeError, ModelViolationError):
        raise StopActorExecutionError(
            "Can't produce RestrictedPCIDevices message. The data are incompatible.")
