from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FirewalldDirectConfig(Model):
    """
    The model contains firewalld direct configuration. The configuration is
    usually located at /etc/firewalld/direct.xml.
    """
    topic = SystemInfoTopic

    has_permanent_configuration = fields.Boolean(default=False)
