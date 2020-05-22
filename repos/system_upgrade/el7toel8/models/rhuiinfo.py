from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class RHUIInfo(Model):
    """
    Subscription-manager details required for the inplace upgrade.
    """
    topic = SystemInfoTopic

    provider = fields.String()
    """ Release the subscription-manager is set to. """
