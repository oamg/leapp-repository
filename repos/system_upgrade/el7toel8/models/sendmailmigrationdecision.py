from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class SendmailMigrationDecision(Model):
    topic = SystemInfoTopic
    migrate_files = fields.List(fields.String())
