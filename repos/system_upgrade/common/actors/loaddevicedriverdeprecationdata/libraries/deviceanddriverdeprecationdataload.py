from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import fetch
from leapp.libraries.common.rpms import get_leapp_packages, LeappComponents
from leapp.libraries.stdlib import api
from leapp.models import DeviceDriverDeprecationData, DeviceDriverDeprecationEntry
from leapp.models.fields import ModelViolationError


def process():
    """
    Loads the device and driver deprecation data and produces a DeviceDriverDeprecationData message with its content.
    It will filter the data on the device_type field, based on the choices set in the StringEnum on the
    DeviceDriverDeprecationEntry model
    """
    # This is how you get the StringEnum choices value, so we can filter based on the model definition
    supported_device_types = set(DeviceDriverDeprecationEntry.device_type.serialize()['choices'])

    data_file_name = 'device_driver_deprecation_data.json'
    # NOTE(pstodulk): load_data_assert raises StopActorExecutionError, see
    # the code for more info. Keeping the handling on the framework in such
    # a case as we have no work to do in such a case here.
    deprecation_data = fetch.load_data_asset(api.current_actor(),
                                             data_file_name,
                                             asset_fulltext_name='Device driver deprecation data',
                                             docs_url='',
                                             docs_title='')

    # Unify all device ids to lowercase
    try:
        for entry in deprecation_data['data']:
            if "device_id" in entry.keys():
                entry["device_id"] = entry.get("device_id").lower()
    except (KeyError, AttributeError, TypeError):
        # this may happen if receiving invalid data
        pass

    try:
        api.produce(
            DeviceDriverDeprecationData(
                entries=[
                    DeviceDriverDeprecationEntry(**entry)
                    for entry in deprecation_data['data']
                    if entry.get('device_type') in supported_device_types
                ]
            )
        )
    except (ModelViolationError, ValueError, KeyError, AttributeError, TypeError) as err:
        # For the listed errors, we expect this to happen only when data is malformed
        # or manually updated. Corrupted data in the upstream is discovered
        # prior the merge thanks to testing. So just suggest the restoration
        # of the file.
        msg = 'Invalid device and driver deprecation data: {}'.format(err)
        hint = (
            'This issue is usually caused by manual update of the {lp} file.'
            ' The data inside is either incorrect or old. To restore the original'
            ' {lp} file, remove it and reinstall the following packages: {rpms}'
            .format(
                lp='/etc/leapp/file/device_driver_deprecation_data.json',
                rpms=', '.join(get_leapp_packages(component=LeappComponents.REPOSITORY))
            )
        )
        raise StopActorExecutionError(msg, details={'hint': hint})
