from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class PCIDevice(Model):
    topic = SystemInfoTopic

    slot = fields.String()
    dev_cls = fields.String()
    vendor = fields.String()
    name = fields.String()
    subsystem_vendor = fields.Nullable(fields.String())
    subsystem_name = fields.Nullable(fields.String())
    physical_slot = fields.Nullable(fields.String())
    rev = fields.Nullable(fields.String())
    progif = fields.Nullable(fields.String())
    driver = fields.Nullable(fields.String())
    modules = fields.Nullable(fields.List(fields.String()))
    numa_node = fields.Nullable(fields.String())


class PCIDevices(Model):
    topic = SystemInfoTopic

    devices = fields.List(fields.Model(PCIDevice))
