from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class RHUIInfo(Model):
    """
    Facts about public cloud provider and RHUI infrastructure
    """
    topic = SystemInfoTopic

    provider = fields.String()
    """ Provider name """
