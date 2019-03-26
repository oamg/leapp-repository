from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class InitrdIncludes(Model):
    """
    List of files (cannonical filesystem paths) to include in RHEL-8 initrd
    """
    topic = SystemInfoTopic

    files = fields.List(fields.String())
