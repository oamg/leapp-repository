from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class NtpMigrationDecision(Model):
    topic = SystemInfoTopic
    migrate_services = fields.List(fields.String())
    config_tgz64 = fields.String()
