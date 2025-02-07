from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class OutdatedKrb5confLocation(Model):
    """
    Provides a list of outdated krb5 conf files.
    """
    topic = SystemInfoTopic

    locations = fields.List(fields.String(), default=[])
    """
    The list with the full path to the krb5 conf files.
    """
