from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FIPSInfo(Model):
    """
    Information about whether the source system has FIPS enabled.
    """
    topic = SystemInfoTopic

    is_enabled = fields.Boolean(default=False)
    """ Is fips enabled on the source system """
