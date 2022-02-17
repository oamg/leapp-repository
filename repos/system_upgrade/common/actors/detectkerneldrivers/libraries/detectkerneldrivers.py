from leapp.libraries.stdlib import api
from leapp.models import ActiveKernelModulesFacts, DetectedDeviceOrDriver, DeviceDriverDeprecationData


def process():
    loaded_drivers = {
        module.filename
        for message in api.consume(ActiveKernelModulesFacts)
        for module in message.kernel_modules
    }
    driver_data = {
        entry.driver_name: entry
        for message in api.consume(DeviceDriverDeprecationData)
        for entry in message.entries
        if not entry.device_id
    }
    api.produce(*[
        DetectedDeviceOrDriver(**driver_data[driver].dump())
        for driver in loaded_drivers
        if driver in driver_data
    ])
