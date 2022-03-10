from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class CryptoPolicyInfo(Model):
    """
    Provide information related to crypto policies
    """
    topic = SystemInfoTopic

    current_policy = fields.String()
    """
    The current used crypto policy: /etc/crypto-policies/state/current

    Contains e.g. 'LEGACY', 'DEFAULT', ...
    """
