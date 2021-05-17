from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class RPM(Model):
    topic = SystemInfoTopic
    name = fields.String()
    epoch = fields.String()
    packager = fields.String()
    version = fields.String()
    release = fields.String()
    arch = fields.String()
    pgpsig = fields.String()
    repository = fields.Nullable(fields.String())


class InstalledRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])


class InstalledRedHatSignedRPM(InstalledRPM):
    pass


class InstalledUnsignedRPM(InstalledRPM):
    pass


class InstalledRPMModuleMapping(Model):
    """Information about which modular stream an installed RPM comes from."""
    topic = SystemInfoTopic
    name = fields.String()
    module = fields.String()
    stream = fields.String()
