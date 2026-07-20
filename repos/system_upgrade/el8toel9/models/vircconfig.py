from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class VircConfig(Model):
    """
    Information about /etc/virc lines that need to be removed during upgrade.
    """
    topic = SystemInfoTopic

    path = fields.String()
    """ Path to the virc configuration file. """
    lines_to_remove = fields.List(fields.String(), default=[])
    """ Lines found in virc that should be removed during upgrade. """
