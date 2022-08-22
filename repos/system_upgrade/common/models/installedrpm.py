from leapp.models import fields, Model
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
    module = fields.Nullable(fields.String())
    stream = fields.Nullable(fields.String())


class InstalledRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])


class InstalledRedHatSignedRPM(InstalledRPM):
    pass


class InstalledUnsignedRPM(InstalledRPM):
    pass
