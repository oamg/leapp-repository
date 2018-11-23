from leapp.models import Model, RPM, fields
from leapp.topics import SystemInfoTopic


class InstalledRedHatSignedRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])


class InstalledUnsignedRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])
