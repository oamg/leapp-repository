from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class LVMConfigDevicesSection(Model):
    """The devices section from the LVM configuration."""
    topic = SystemInfoTopic

    use_devicesfile = fields.Boolean()
    """
    Determines whether only the devices in the devices file are used by LVM. Note
    that the default value changed on the RHEL 9 to True.
    """

    devicesfile = fields.String(default="system.devices")
    """
    Defines the name of the devices file that should be used. The default devices
    file is located in '/etc/lvm/devices/system.devices'.
    """


class LVMConfig(Model):
    """LVM configuration split into sections."""
    topic = SystemInfoTopic

    devices = fields.Model(LVMConfigDevicesSection)
