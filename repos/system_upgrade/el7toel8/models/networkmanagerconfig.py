from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class NetworkManagerConfig(Model):
    """The model contains NetworkManager configuration."""
    topic = SystemInfoTopic
    dhcp = fields.String(default='')
