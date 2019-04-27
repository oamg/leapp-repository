from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class CupsFiltersModel(Model):
    topic = SystemInfoTopic
    migrateable = fields.Boolean()
