from leapp.models import CustomTargetRepository, fields, Model
from leapp.topics import SystemFactsTopic


class TargetOSInstallationImage(Model):
    """
    An installation image of a target OS requested to be the source of target OS packages.
    """
    topic = SystemFactsTopic
    path = fields.String()
    mountpoint = fields.String()
    repositories = fields.List(fields.Model(CustomTargetRepository))
    rhel_version = fields.String(default='')
    was_mounted_successfully = fields.Boolean(default=False)
