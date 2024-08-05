from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PamUserDbLocation(Model):
    """
    Provides a list of all database files for pam_userdb
    """
    topic = SystemInfoTopic

    locations = fields.List(fields.String(), default=[])
    """
    The list with the full path to the database files.
    """
