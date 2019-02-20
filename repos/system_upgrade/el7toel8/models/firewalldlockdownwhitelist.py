from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class FirewalldLockdownWhitelist(Model):
    """The model contains firewalld Lockdown Whitelist configuration."""
    topic = SystemInfoTopic
    firewall_config_command = fields.String(default='')
