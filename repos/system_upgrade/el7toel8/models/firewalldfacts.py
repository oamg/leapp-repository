from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FirewalldFacts(Model):
    """The model contains firewalld configuration."""
    topic = SystemInfoTopic

    firewall_config_command = fields.String(default='')
    ebtablesTablesInUse = fields.List(fields.String(), default=[])
    ipsetTypesInUse = fields.List(fields.String(), default=[])
