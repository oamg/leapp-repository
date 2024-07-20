from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class NetworkManagerConfig(Model):
    """The model contains NetworkManager configuration."""
    topic = SystemInfoTopic
    dhcp = fields.String(default='')
