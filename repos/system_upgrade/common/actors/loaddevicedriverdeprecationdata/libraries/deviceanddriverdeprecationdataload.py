import json

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import fetch
from leapp.libraries.stdlib import api
from leapp.models import DeviceDriverDeprecationData, DeviceDriverDeprecationEntry


def _load_file():
    try:
        return json.loads(
            fetch.read_or_fetch('device_driver_deprecation_data.json'))
    except ValueError:
        raise StopActorExecutionError(
            'The device driver deprecation data file is invalid: file does not contain a valid JSON object.',
            details={'hint': ('Read documentation at the following link for more'
                              ' information about how to retrieve the valid file:'
                              ' https://access.redhat.com/articles/3664871')})


def process():
    """
    Loads the device and driver deprecation data and produces a DeviceDriverDeprecationData message with its content.
    It will filter the data on the device_type field, based on the choices set in the StringEnum on the
    DeviceDriverDeprecationEntry model
    """
    # This is how you get the StringEnum choices value, so we can filter based on the model definition
    supported_device_types = set(DeviceDriverDeprecationEntry.device_type.serialize()['choices'])
    api.produce(
        DeviceDriverDeprecationData(
            entries=[
                DeviceDriverDeprecationEntry(**entry)
                for entry in _load_file()['data']
                if entry.get('device_type') in supported_device_types
            ]
        )
    )
