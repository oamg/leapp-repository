from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class CurrentKernel(Model):
    topic = SystemInfoTopic
    version = fields.String()
    release = fields.String()
    arch = fields.String()
