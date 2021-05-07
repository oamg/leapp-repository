import json

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import fetch
from leapp.libraries.stdlib import api
from leapp.models import RestrictedPCIDevices, RestrictedPCIDevice
from leapp.models.fields import ModelViolationError


try:
    # python3
    from json import JSONDecodeError  # pylint: disable=ungrouped-imports
except ImportError:
    # python2
    JSONDecodeError = ValueError

UNSUPPORTED_DRIVER_NAMES_FILE = 'unsupported_driver_names.json'
UNSUPPORTED_PCI_IDS_FILE = 'unsupported_pci_ids.json'


def current_major_version():
    return api.current_actor().configuration.version.source.split('.')[0]


def target_major_version():
    return api.current_actor().configuration.version.target.split('.')[0]


def _raise_error(msg, details=None):
    if detail is None:
        details = {}
    details['hint'] = (
        'Read documentation at https://access.redhat.com/articles/3664871'
        ' for more information about how to retrieve the file.'
    )

    raise StopActorExecutionError(msg, details=details)

def _check_data(dev):
    """
    Raise the StopActorExecutionError when data for the source or target system
    not set.

    We expect always data at least for the source and the target system.
    If data is not set it iss considered as invalid or incompatible with
    actors in this repository.
    """
    for prefix in ['available_rhel', 'supported_rhel']:
        source_key = '{}{}'.format(prefix, current_major_version)
        target_key = '{}{}'.format(prefix, target_major_version)
        if source_key not in dev or target_key not in dev:
            _raise_error(
                'Cannot produce the RestrictedPCIDevices message. The data is incompatible.',
                details={
                    'details': 'Data about PCI devices for the current or target system is missing.'
                },
            )


def _get_the_list(dev, prefix):
    """
    The dev dict has prefixX keys (X in {7, 8, 9}) with 0||1 values. Get list
    of X for values == 1.

    X corresponds to the major version of RHEL.
    E.g.
        'available_rhel7': 1,
        'supported_rhel7': 0,
        'available_rhel8': 0,
        'supported_rhel8': 0,
    If prefix == 'available_rhel', returns [7] in this case.
    """
    result = []

    for key in dev.keys():
        if not key.startswith(prefix):
            continue
        try:
            result.append(int(key[len(prefix):]))
        except ValueError:
            # This will just inform us in case the data structure is changed.
            # Currently this cannot happen. As well, such a change is not expected
            # to be harmful for the upgrade.
            api.current_logger().warning('Unknown field in restricted PCI data: {}'.format())

    result.sort()
    return result 


def get_restricted_devices(filename):
    """
    Load the specified data from the filename or the online service and generate
    the list of RestrictedPCIDevice objects.

    The data for both data files have the same format. But unfortunately the
    data structure is not so friendly for another processing so let's use
    process the data now to make another work with it more friendly.
    """
    try:
        json_data = fetch.read_or_fetch(UNSUPPORTED_DRIVER_NAMES_FILE)
        data = json.loads(json_data, encoding='utf-8')
    except (JSONDecodeError, UnicodeDecodeError):
        _raise_error(
            'The required leapp data has invalid JSON format and cannot be decoded.'
            details={'data source': filename}
        )

    devices = []
    for dev in data['devices'].values():
        _check_data(dev)
        try:
            devices.append(RestrictedPCIDevice(
                pci_id=dev.get('pci_id', None),
                driver_name=dev.get('driver_name', None),
                device_name=dev.get('device_name', None),
                available_rhel7=dev['available_rhel7'],
                available_rhel8=dev['available_rhel8'],
                available_rhel9=dev['available_rhel9'],
                supported_rhel7=dev['supported_rhel7'],
                supported_rhel8=dev['supported_rhel8'],
                supported_rhel9=dev['supported_rhel9'],
                available=_get_the_list(dev, 'available_rhel'),
                supported=_get_the_list(dev, 'supported_rhel'),
                comment=dev['comment'],
            ))
        except (KeyError, ModelViolationError) as err:
            api.current_logger().error('PCI data ({}) is incompatible: {}'.format(filename, str(err)))
            _raise_error(
                'The data about restricted PCI devices is incompatible.'
                details={'data source': filename}
            )

    return devices


def produce_restricted_pcis():
    """
    Produce RestrictedPCIDevices message from the required data files.
    """
    api.produce(RestrictedPCIDevices(
        driver_names=get_restricted_devices(UNSUPPORTED_DRIVER_NAMES_FILE),
        pci_ids=get_restricted_devices(UNSUPPORTED_PCI_IDS_FILE),
    )
