from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class BlackListError(Model):
    """
    Provides an entry for all disabled CAs in one of blacklist directoriesi
    which needs to be moved to blocklist.
    """
    topic = SystemInfoTopic

    sourceDir = fields.String()
    """
    The path of the blacklist directory where distrusted certs reside.
    """

    targetDir = fields.String()
    """
    The path of the blocklist directory where distructed certs should reside.
    """

    error = fields.String()
    """
    Errors string from the OS or the LEAPP run process
    """
