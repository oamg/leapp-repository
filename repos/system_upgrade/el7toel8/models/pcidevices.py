from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class PCIDevice(Model):
    topic = SystemInfoTopic

    slot = fields.String()
    cls = fields.String()
    vendor = fields.String()
    name = fields.String()
    subsystem_vendor = fields.String()
    subsystem_name = fields.String()
    rev = fields.String()
    progif = fields.String()


class PCIDevices(Model):
    topic = SystemInfoTopic

    devices = fields.List(fields.Model(PCIDevice))
