from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class BrlttyMigrationDecision(Model):
    topic = SystemInfoTopic
    migrate_file = fields.String()
    migrate_bt = fields.Boolean()
    migrate_espeak = fields.Boolean()
