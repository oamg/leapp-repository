from leapp.models import Model, RPM, fields
from leapp.topics import SystemInfoTopic


class InstalledRedHatSignedRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), required=True, default=[])


class InstalledUnsignedRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), required=True, default=[])
