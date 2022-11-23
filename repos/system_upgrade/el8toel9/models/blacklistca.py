from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class BlackListCA(Model):
    """
    Provides an entry for all disabled CAs in one of blacklist directoriesi
    which needs to be moved to blocklist.
    """
    topic = SystemInfoTopic

    source = fields.String()
    """
    The full path to the file in the blacklist directory.
    """

    sourceDir = fields.String()
    """
    The path of the blacklist directory where source resides.
    """

    target = fields.String()
    """
    The full path to where the file should be migrated to.
    """

    targetDir = fields.String()
    """
    The path of the blocklist directory where the target resides
    """
