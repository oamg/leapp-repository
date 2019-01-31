from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class PCIDevice(Model):
    topic = SystemInfoTopic

    slot = fields.String()
    dev_cls = fields.String()
    vendor = fields.String()
    name = fields.String()
    subsystem_vendor = fields.String()
    subsystem_name = fields.String()
    rev = fields.Nullable(fields.String())
    progif = fields.Nullable(fields.String())


class PCIDevices(Model):
    topic = SystemInfoTopic

    devices = fields.List(fields.Model(PCIDevice))
