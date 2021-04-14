import errno
import json
import os

import urllib3

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevices
from leapp.models.fields import ModelViolationError


try:
    # python3
    from json import JSONDecodeError  # pylint: disable=ungrouped-imports
except ImportError:
    # python2
    JSONDecodeError = ValueError

REQUEST_TIMEOUT = 0.5  # TODO Consider moving it to the leapp env var
UNSUPPORTED_DRIVER_NAMES_GLOBAL_FILE = os.path.join(
    "/etc/leapp/files", "unsupported_driver_names.json"
)
UNSUPPORTED_PCI_IDS_GLOBAL_FILE = os.path.join(
    "/etc/leapp/files", "unsupported_pci_ids.json"
)

PCIS_HOST_DEFAULT = "cloud.stage.redhat.com"


def get_restricted_pcis(http):
    """
    Get data about restricted driver names and unsupported pci_ids online.

    The function makes API call to the web service, which provides
    these data.

    :param urllib3.PoolManager http: pool manager instance
    :returns: Tuple[dict, dict]
    """
    # TODO this constant should be above the scope of this func.
    #   However due to the way how actor tested with CurrentActorMocked
    #   we can't do this.
    API_URL = "http://{host}/api/pes/".format(
        host=get_env(
            "LEAPP_DEVEL_PCIS_HOST",
            default=PCIS_HOST_DEFAULT,
        ),
    )
    headers = urllib3.make_headers(basic_auth="drehak@redhat.com:redhat")

    unsupported_driver_names = http.request(
        "GET",
        API_URL + "unsupported_driver_names.json",
        timeout=REQUEST_TIMEOUT,
        headers=headers,
    )
    unsupported_pci_ids = http.request(
        "GET",
        API_URL + "unsupported_pci_ids.json",
        timeout=REQUEST_TIMEOUT,
        headers=headers,
    )

    unsupported_driver_names = json.loads(
        unsupported_driver_names.data.decode("utf-8")
    )
    unsupported_pci_ids = json.loads(unsupported_pci_ids.data.decode("utf-8"))
    return unsupported_driver_names, unsupported_pci_ids


def get_restricted_pcis_offline(driver_names_file, pci_ids_file, _open=open):
    """
    Get data about restricted driver names and unsupported pci_ids offline.

    The function takes the data from locally stored json files in the given
    location.

    :param _open: made to make the testing easy
    """
    with _open(driver_names_file) as f:
        unsupported_driver_names = json.load(f)
    with _open(pci_ids_file) as f:
        unsupported_pci_ids = json.load(f)
    return unsupported_driver_names, unsupported_pci_ids


def produce_restricted_pcis():
    """
    Produce RestrictedPCIDevice message from the online or offline sources.

    The data sources preference order is the following:
    1. We try to get the data from the /etc/leapp/files
    2. We try to get the data from the only web service
    """
    unsupported_driver_names = {"devices": {}}
    unsupported_pci_ids = {"devices": {}}
    # trying get data in leapp files
    try:
        api.current_logger().info(
            "Trying get restricted PCI data from the /etc/leapp/files..."
        )
        unsupported_driver_names, unsupported_pci_ids = get_restricted_pcis_offline(
            driver_names_file=UNSUPPORTED_DRIVER_NAMES_GLOBAL_FILE,
            pci_ids_file=UNSUPPORTED_PCI_IDS_GLOBAL_FILE,
        )
        api.current_logger().info("Data received from /etc/leapp/files.")
    # no files
    except EnvironmentError as e:
        if e.errno == errno.ENOENT and not (
            os.path.islink(UNSUPPORTED_DRIVER_NAMES_GLOBAL_FILE)
            or os.path.islink(UNSUPPORTED_PCI_IDS_GLOBAL_FILE)
        ):
            # trying to get files online
            try:
                api.current_logger().info(
                    "Trying get restricted PCI data online..."
                )
                http = urllib3.PoolManager()
                (
                    unsupported_driver_names,
                    unsupported_pci_ids,
                ) = get_restricted_pcis(http)
                api.current_logger().info(
                    "Data received from the online source."
                )
            # mcs is not available or return a bad json format
            except (urllib3.exceptions.MaxRetryError, JSONDecodeError):
                raise StopActorExecutionError(
                    message=(
                        "Can't get the data about restricted PCI devices "
                        "from any available sources."
                    )
                )
        else:
            raise StopActorExecutionError(
                "The required files are presented in the /etc/leapp/files. "
                "However, they can't be read by the system (i.e. "
                "broken symlink, IO error)."
            )
    # files exists, but bad json format
    except (JSONDecodeError, UnicodeDecodeError):
        raise StopActorExecutionError(
            "The required files are presented in the /etc/leapp/files. "
            "However, they have invalid JSON format and can't be decoded."
        )
    finally:
        # trying to produce the message from received data
        try:
            api.produce(
                RestrictedPCIDevices.create(
                    {
                        "driver_names": tuple(
                            unsupported_driver_names["devices"].values()
                        ),
                        "pci_ids": tuple(
                            unsupported_pci_ids["devices"].values()
                        ),
                    },
                )
            )
        # bad data format
        except (KeyError, AttributeError, ModelViolationError):
            raise StopActorExecutionError(
                "Can't produce RestrictedPCIDevices message. The data are incompatible."
            )
