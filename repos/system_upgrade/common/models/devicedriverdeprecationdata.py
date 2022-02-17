from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class DeviceDriverDeprecationEntry(Model):
    """
    Describes a device or driver deprecated in RHEL
    """
    topic = SystemFactsTopic

    deprecation_announced = fields.String()
    """
    This field should contain a X.Y version in which version
    of RHEL the deprecation of the described driver or device was announced.

    NOTE: The value is not enforced to be in the X.Y format and might be empty.
          As not all data entries do contain this relevant information.
    """

    device_id = fields.String()
    """
    If this entry describes a device, this field will contain an identification
    string, relevant to the device.

    This identification string might contain sets of numbers {1,2,3},
    ranges [1-3] or even sets of ranges {[1-3],[5-9]} or a wildcard * which
    should match any number.

    Examples:
    - Range:            'x86_64:intel:6:[56-57]'
    - Set:              'x86_64:amd:23:{1,17,49}'
    - Set of Ranges:    'x86_64:amd:23:{[2-16],[18-48],[50-255]}'
    - Wildcard:         'x86_64:amd:21:*'
    """

    device_type = fields.StringEnum(choices=['pci', 'cpu'])
    """

    NOTE: Other devices might come later. The following values have been
    described:
    - 'usb'
    - 'video_adapter'
    - 'firewire'
    - 'qemu_machine'
    However they aren't in use yet. Since we wouldn't support it for
    now, we can extend it once we support it and just filter the ones supported,
    by leapp.
    """

    device_name = fields.String()
    """
    Human readable name of the device in question - Could be used to display.
    """

    driver_name = fields.String()
    """
    Name of the kernel driver for the device, or just a plain driver name.
    Might be an empty string.
    """

    available_in_rhel = fields.List(fields.Integer())
    """
    List of major version numbers, in which the device/driver can be found.
    If the target major version number is not in this list, the upgrade must
    be inhibited to avoid problems on boot.
    """
    maintained_in_rhel = fields.List(fields.Integer())
    """
    List of major version numbers, in which the device/driver is maintained. That
    means, that in those versions the device/driver actively gets patches and
    bug fixes.
    If the target major version number is not in this list, but is in the
    available_in_rhel list, a warning should be generated, but the upgrade must
    NOT be inhibited.
    """


class DetectedDeviceOrDriver(DeviceDriverDeprecationEntry):
    """
    DetectedDeviceOrDriver is used for reporting unsupported drivers or devices
    """


class DeviceDriverDeprecationData(Model):
    """
    Contains data related to deprecated devices and drivers in RHEL
    """
    topic = SystemFactsTopic

    entries = fields.List(fields.Model(DeviceDriverDeprecationEntry))
    """
    A list of entries describing deprecated devices and drivers
    """
