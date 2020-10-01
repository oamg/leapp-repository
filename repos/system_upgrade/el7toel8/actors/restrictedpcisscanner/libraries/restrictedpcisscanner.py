import json
import os

import urllib3

from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevices

REQUEST_TIMEOUT = 0.5
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
UNSUPPORTED_DRIVER_NAMES_FILE = os.path.join(
    CUR_DIR, "..", "data", "unsupported_driver_names.json"
)
UNSUPPORTED_PCI_IDS_FILE = os.path.join(
    CUR_DIR, "..", "data", "unsupported_pci_ids.json"
)

PCIS_HOST_DEFAULT = "10.0.79.153:8000"
API_VERSION = "v1"


def get_restricted_pcis(http, update_local_data=False):
    """
    Get data about unsupported driver names and unsupported pci_ids.

    The function makes API call to the web service, which provides
    these data.

    :param urllib3.PoolManager http: pool manager instance
    :param bool update_local_data: if True writes the received data to
        the corresponding json data files (inside ../data dir)

    :returns: Tuple[dict, dict]
    """
    # TODO this constant should be above the scope of this func.
    #   However due to the way how actor tested with CurrentActorMocked
    #   we can't do this.
    API_URL = (
        "http://"
        + get_env(
            "LEAPP_DEVEL_PCIS_HOST",
            default=PCIS_HOST_DEFAULT,
        )
        + "/api/"
        + API_VERSION
        + "/"
    )
    unsupported_driver_names = http.request(
        "GET",
        API_URL + "unsupported_driver_names/",
        timeout=REQUEST_TIMEOUT,
    )
    unsupported_pci_ids = http.request(
        "GET",
        API_URL + "unsupported_pci_ids/",
        timeout=REQUEST_TIMEOUT,
    )

    unsupported_driver_names = json.loads(
        unsupported_driver_names.data.decode("utf-8")
    )
    unsupported_pci_ids = json.loads(unsupported_pci_ids.data.decode("utf-8"))
    if update_local_data:
        with open(UNSUPPORTED_DRIVER_NAMES_FILE, mode="w") as f:
            json.dump(unsupported_driver_names, f)
        with open(UNSUPPORTED_PCI_IDS_FILE, mode="w") as f:
            json.dump(unsupported_pci_ids, f)
    return unsupported_driver_names, unsupported_pci_ids


def get_restricted_pcis_offline():
    """
    Get data about unsupported driver names and unsupported pci_ids.

    The function takes the data from locally stored json files.
    """
    with open(UNSUPPORTED_DRIVER_NAMES_FILE) as f:
        unsupported_driver_names = json.load(f)
    with open(UNSUPPORTED_PCI_IDS_FILE) as f:
        unsupported_pci_ids = json.load(f)
    return unsupported_driver_names, unsupported_pci_ids


def produce_restricted_pcis():
    """
    Produce RestrictedPCIDevice message from online or offline source.

    If it is impossible to get the data online, then a warning generated and
    the data are taken from the locally stored json files.
    """
    try:
        api.current_logger().info("Trying get restricted PCI data online...")
        http = urllib3.PoolManager()
        unsupported_driver_names, unsupported_pci_ids = get_restricted_pcis(
            http
        )
        api.current_logger().info("Online method succeeded.")
    except urllib3.exceptions.MaxRetryError:
        api.current_logger().warning(
            "Using offline way to get restricted PCI data."
        )
        (
            unsupported_driver_names,
            unsupported_pci_ids,
        ) = get_restricted_pcis_offline()
        api.current_logger().info("Offline method succeeded.")
    finally:
        api.produce(
            RestrictedPCIDevices(
                driver_names=unsupported_driver_names,
                pci_ids=unsupported_pci_ids,
            )
        )
