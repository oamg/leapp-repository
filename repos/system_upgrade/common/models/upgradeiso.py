from leapp.models import CustomTargetRepository, fields, Model
from leapp.topics import SystemFactsTopic


class TargetOSInstallationImage(Model):
    """
    An installation image of a target OS requested to be the source of target OS packages.

    Note: `rhel_version` is deprecated, use `os_version` instead.
    """
    topic = SystemFactsTopic
    path = fields.String()
    mountpoint = fields.String()
    repositories = fields.List(fields.Model(CustomTargetRepository))
    rhel_version = fields.String(default='')
    """
    The RHEL version provided by the ISO

    DEPRECATED - use os_version instead.
    """

    os_version = fields.String(default='')
    """
    The OS version provided by the ISO

    The version is the full version available in /etc/<distro>-release,
    i.e. it is in the versioning schema used by the distribution, which is
    usually MAJOR.MINOR except for CentOS Stream where it's MAJOR.
    """

    was_mounted_successfully = fields.Boolean(default=False)
