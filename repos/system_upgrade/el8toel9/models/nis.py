from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class NISConfig(Model):
    """
    The model contains NIS packages configuration status.
    """
    topic = SystemInfoTopic

    nis_not_default_conf = fields.List(fields.String(), default=[])
    """
    List of names of NIS packages with modified default configuration.

    e.g. ["ypbind", "ypserv"]
    """
