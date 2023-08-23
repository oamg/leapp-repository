from leapp.libraries.common import fetch
from leapp.libraries.stdlib import api
from leapp.models import DeviceDriverDeprecationData, DeviceDriverDeprecationEntry


def process():
    """
    Loads the device and driver deprecation data and produces a DeviceDriverDeprecationData message with its content.
    It will filter the data on the device_type field, based on the choices set in the StringEnum on the
    DeviceDriverDeprecationEntry model
    """
    # This is how you get the StringEnum choices value, so we can filter based on the model definition
    supported_device_types = set(DeviceDriverDeprecationEntry.device_type.serialize()['choices'])

    data_file_name = 'device_driver_deprecation_data.json'
    deprecation_data = fetch.load_data_asset(api.current_actor(),
                                             data_file_name,
                                             asset_fulltext_name='Device driver deprecation data',
                                             docs_url='',
                                             docs_title='')

    api.produce(
        DeviceDriverDeprecationData(
            entries=[
                DeviceDriverDeprecationEntry(**entry)
                for entry in deprecation_data['data']
                if entry.get('device_type') in supported_device_types
            ]
        )
    )
